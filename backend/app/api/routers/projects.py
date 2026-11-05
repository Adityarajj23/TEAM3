from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import serializers as S
from app.api.deps import (
    PageParams,
    Principal,
    accessible_project_ids,
    current_principal,
    get_project_checked,
    page_params,
    paginate,
    require,
)
from app.core.errors import BadRequest, Conflict, NotFound
from app.db.base import get_db, utcnow
from app.db.models import (
    Defect,
    Environment,
    Module,
    Organisation,
    Project,
    ProjectMember,
    Requirement,
    TestCase,
    TestSuite,
    User,
)
from app.services import audit
from app.services.analytics import coverage_by_project

router = APIRouter(prefix="/projects", tags=["projects"])


def _with_stats(db: Session, p: Project) -> dict:
    out = S.project(p)
    out["stats"] = {
        "requirements": db.scalar(select(func.count()).select_from(Requirement).where(Requirement.project_id == p.id)),
        "tests": db.scalar(select(func.count()).select_from(TestCase).where(TestCase.project_id == p.id)),
        "suites": db.scalar(select(func.count()).select_from(TestSuite).where(TestSuite.project_id == p.id)),
        "open_defects": db.scalar(select(func.count()).select_from(Defect).where(
            Defect.project_id == p.id, Defect.approval_status == "approved",
            Defect.status.notin_(["verified", "closed"]))),
        "members": db.scalar(select(func.count()).select_from(ProjectMember).where(ProjectMember.project_id == p.id)),
    }
    cov = coverage_by_project(db, [p.id])
    out["stats"]["coverage_pct"] = cov[0]["coverage_pct"] if cov else 0.0
    return out


@router.get("")
def list_projects(pp: PageParams = Depends(page_params), status: str | None = None,
                  p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    stmt = select(Project).where(Project.id.in_(accessible_project_ids(db, p) or [-1]))
    if status:
        stmt = stmt.where(Project.status == status)
    if pp.q:
        stmt = stmt.where(Project.name.ilike(f"%{pp.q}%") | Project.key.ilike(f"%{pp.q}%"))
    return paginate(db, stmt, pp, {"name": Project.name, "key": Project.key, "updated_at": Project.updated_at},
                    Project.key, lambda x: _with_stats(db, x))


class ProjectIn(BaseModel):
    key: str = Field(min_length=2, max_length=10)
    name: str = Field(min_length=3, max_length=200)
    description: str = ""


@router.post("", status_code=201)
def create_project(body: ProjectIn, p: Principal = Depends(require("project.admin")), db: Session = Depends(get_db)):
    key = body.key.upper()
    if not re.fullmatch(r"[A-Z0-9_-]{2,10}", key):
        raise BadRequest("Project key must be 2-10 letters/numbers/hyphens")
    if db.execute(select(Project).where(Project.key == key)).scalar_one_or_none():
        raise Conflict("Project key already in use")
    org = db.execute(select(Organisation)).scalars().first()
    proj = Project(key=key, name=body.name, description=body.description, organisation_id=org.id, owner_id=p.id)
    db.add(proj)
    db.flush()
    db.add(ProjectMember(project_id=proj.id, user_id=p.id, project_role="owner"))
    db.add(Environment(project_id=proj.id, name="QA — Reference HCM 1.0", hcm_version="1.0", is_default=True))
    db.add(Environment(project_id=proj.id, name="Fix candidate — Reference HCM 1.1", hcm_version="1.1"))
    audit.record(db, p.id, "project.created", "project", proj.id, proj.key, proj.id)
    db.commit()
    return _with_stats(db, proj)


class RepoImportIn(BaseModel):
    repo_url: str = Field(default="https://github.com/sohan10012/EchoBox.git")
    branch: str = "main"
    project_key: str = "ECHO"
    project_name: str = "EchoBox — Anonymous Conversation Platform"
    dry_run: bool = False


@router.post("/import-repo", status_code=201)
def import_repository(body: RepoImportIn, p: Principal = Depends(require("project.admin")),
                      db: Session = Depends(get_db)):
    from app.core.config import REPO_ROOT
    from app.services.repo_ingest import analyze_repository, ingest_echobox_project

    # Locate repository: check var/repos/EchoBox or clone
    repo_name = body.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    target_dir = REPO_ROOT / "var" / "repos" / repo_name
    if not target_dir.exists():
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        import subprocess
        subprocess.run(["git", "clone", "--depth", "1", "-b", body.branch, body.repo_url, str(target_dir)],
                       check=True, timeout=60)

    analysis = analyze_repository(target_dir)
    if body.dry_run:
        return {"dry_run": True, "analysis": analysis.__dict__}

    proj = ingest_echobox_project(db, p.id, target_dir)
    return {
        "ok": True,
        "project": _with_stats(db, proj),
        "analysis": analysis.__dict__
    }


@router.get("/{project_id}")
def get_project(project_id: int, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    proj = get_project_checked(db, p, project_id)
    out = _with_stats(db, proj)
    out["modules"] = [S.module(m) for m in db.execute(select(Module).where(Module.project_id == proj.id)).scalars()]
    out["environments"] = [S.environment(e) for e in
                           db.execute(select(Environment).where(Environment.project_id == proj.id)).scalars()]
    members = db.execute(select(ProjectMember, User).join(User, User.id == ProjectMember.user_id)
                         .where(ProjectMember.project_id == proj.id)).all()
    out["members"] = [{"user": S.user(u), "project_role": pm.project_role} for pm, u in members]
    return out


class ProjectPatch(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = None
    status: str | None = Field(None, pattern="^(active|archived)$")


@router.patch("/{project_id}")
def update_project(project_id: int, body: ProjectPatch, p: Principal = Depends(require("project.admin")),
                   db: Session = Depends(get_db)):
    proj = get_project_checked(db, p, project_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(proj, k, v)
    proj.updated_at = utcnow()
    action = "project.archived" if body.status == "archived" else "project.updated"
    audit.record(db, p.id, action, "project", proj.id, proj.key, proj.id, body.model_dump(exclude_none=True))
    db.commit()
    return _with_stats(db, proj)


class MemberIn(BaseModel):
    user_id: int
    project_role: str = "member"


@router.post("/{project_id}/members", status_code=201)
def add_member(project_id: int, body: MemberIn, p: Principal = Depends(require("project.admin")),
               db: Session = Depends(get_db)):
    proj = get_project_checked(db, p, project_id)
    if db.get(User, body.user_id) is None:
        raise NotFound("User")
    if db.execute(select(ProjectMember).filter_by(project_id=proj.id, user_id=body.user_id)).scalar_one_or_none():
        raise Conflict("User is already a member")
    db.add(ProjectMember(project_id=proj.id, user_id=body.user_id, project_role=body.project_role))
    audit.record(db, p.id, "project.member_added", "project", proj.id, proj.key, proj.id, {"user_id": body.user_id})
    db.commit()
    return {"ok": True}


@router.delete("/{project_id}/members/{user_id}")
def remove_member(project_id: int, user_id: int, p: Principal = Depends(require("project.admin")),
                  db: Session = Depends(get_db)):
    proj = get_project_checked(db, p, project_id)
    pm = db.execute(select(ProjectMember).filter_by(project_id=proj.id, user_id=user_id)).scalar_one_or_none()
    if pm is None:
        raise NotFound("Membership")
    db.delete(pm)
    audit.record(db, p.id, "project.member_removed", "project", proj.id, proj.key, proj.id, {"user_id": user_id})
    db.commit()
    return {"ok": True}


class ModuleIn(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=2, max_length=200)
    description: str = ""


@router.post("/{project_id}/modules", status_code=201)
def add_module(project_id: int, body: ModuleIn, p: Principal = Depends(require("project.admin")),
               db: Session = Depends(get_db)):
    proj = get_project_checked(db, p, project_id)
    if db.execute(select(Module).filter_by(project_id=proj.id, code=body.code.upper())).scalar_one_or_none():
        raise Conflict("Module code already exists")
    m = Module(project_id=proj.id, code=body.code.upper(), name=body.name, description=body.description)
    db.add(m)
    audit.record(db, p.id, "module.created", "module", None, body.code.upper(), proj.id)
    db.commit()
    return S.module(m)


class EnvIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    kind: str = Field("reference_hcm", pattern="^(reference_hcm|web)$")
    hcm_version: str | None = Field(None, pattern=r"^1\.[01]$")
    base_url: str | None = Field(None, max_length=500)


@router.post("/{project_id}/environments", status_code=201)
def add_environment(project_id: int, body: EnvIn, p: Principal = Depends(require("project.admin")),
                    db: Session = Depends(get_db)):
    proj = get_project_checked(db, p, project_id)
    if body.kind == "reference_hcm" and not body.hcm_version:
        raise BadRequest("Reference HCM environments need hcm_version 1.0 or 1.1")
    if body.kind == "web" and not (body.base_url or "").startswith(("http://", "https://")):
        raise BadRequest("Web environments need an http(s) base_url")
    e = Environment(project_id=proj.id, **body.model_dump())
    db.add(e)
    audit.record(db, p.id, "environment.created", "environment", None, body.name, proj.id)
    db.commit()
    return S.environment(e)
