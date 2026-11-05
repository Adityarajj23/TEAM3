from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import serializers as S
from app.api.deps import PageParams, Principal, current_principal, page_params, paginate, require
from app.core.errors import BadRequest, Conflict, NotFound
from app.core.security import hash_password
from app.db.base import get_db
from app.db.models import Role, User, UserRole
from app.services import audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(pp: PageParams = Depends(page_params), p: Principal = Depends(current_principal),
               db: Session = Depends(get_db)):
    stmt = select(User)
    if pp.q:
        stmt = stmt.where(User.full_name.ilike(f"%{pp.q}%") | User.email.ilike(f"%{pp.q}%"))
    return paginate(db, stmt, pp, {"name": User.full_name, "email": User.email}, User.full_name, S.user)


class UserIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    full_name: str = Field(min_length=2, max_length=200)
    title: str | None = None
    roles: list[str] = Field(min_length=1)
    password: str | None = Field(None, min_length=12, max_length=256)


@router.post("", status_code=201)
def create_user(body: UserIn, p: Principal = Depends(require("user.admin")), db: Session = Depends(get_db)):
    if db.execute(select(User).where(User.email == body.email.lower())).scalar_one_or_none():
        raise Conflict("A user with this email already exists")
    roles = db.execute(select(Role).where(Role.name.in_(body.roles))).scalars().all()
    if len(roles) != len(set(body.roles)):
        raise BadRequest("Unknown role")
    u = User(email=body.email.lower(), full_name=body.full_name, title=body.title,
             password_hash=hash_password(body.password) if body.password else None, can_login=bool(body.password))
    db.add(u)
    db.flush()
    for r in roles:
        db.add(UserRole(user_id=u.id, role_id=r.id))
    audit.record(db, p.id, "user.created", "user", u.id, u.email, details={"roles": body.roles})
    db.commit()
    db.refresh(u)
    return S.user(u)


class UserPatch(BaseModel):
    is_active: bool | None = None
    roles: list[str] | None = None
    title: str | None = None


@router.patch("/{user_id}")
def update_user(user_id: int, body: UserPatch, p: Principal = Depends(require("user.admin")),
                db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None:
        raise NotFound("User")
    if body.is_active is False and u.id == p.id:
        raise BadRequest("You cannot deactivate your own account")
    if body.is_active is not None:
        u.is_active = body.is_active
    if body.title is not None:
        u.title = body.title
    if body.roles is not None:
        roles = db.execute(select(Role).where(Role.name.in_(body.roles))).scalars().all()
        if len(roles) != len(set(body.roles)) or not roles:
            raise BadRequest("Unknown role")
        for ur in list(u.roles):
            db.delete(ur)
        db.flush()
        for r in roles:
            db.add(UserRole(user_id=u.id, role_id=r.id))
    audit.record(db, p.id, "user.updated", "user", u.id, u.email, details=body.model_dump(exclude_none=True))
    db.commit()
    db.refresh(u)
    return S.user(u)


@router.get("/roles")
def roles(p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    return [{"name": r.name, "description": r.description} for r in db.execute(select(Role)).scalars()]
