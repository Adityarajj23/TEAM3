from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import serializers as S
from app.api.deps import Principal, accessible_project_ids, current_principal
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import CSRF_COOKIE, SESSION_COOKIE, hash_token, new_token, verify_password
from app.db.base import get_db, utcnow
from app.db.models import LoginAttempt, Project, User, UserSession
from app.domain.enums import PERMISSIONS
from app.services import audit

router = APIRouter(prefix="/auth", tags=["authentication"])
MAX_FAILURES, WINDOW_MIN = 5, 15


class LoginIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    password: str = Field(min_length=1, max_length=256)


def _me(db: Session, p_user: User, roles: set[str], csrf: str) -> dict:
    perms = set()
    for r in roles:
        perms |= PERMISSIONS.get(r, set())
    return {"user": S.user(p_user), "roles": sorted(roles), "permissions": sorted(perms), "csrf_token": csrf}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    s = get_settings()
    email = body.email.lower()
    ip = request.client.host if request.client else None
    since = utcnow() - timedelta(minutes=WINDOW_MIN)
    failures = db.scalar(select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.email == email, LoginAttempt.success.is_(False), LoginAttempt.created_at >= since)) or 0
    if failures >= MAX_FAILURES:
        raise AppError(429, "login_throttled", f"Too many failed attempts. Try again in {WINDOW_MIN} minutes.")
    user = db.execute(select(User).where(func.lower(User.email) == email)).scalar_one_or_none()
    ok = bool(user and user.is_active and user.can_login and verify_password(body.password, user.password_hash))
    db.add(LoginAttempt(email=email, ip=ip, success=ok))
    if not ok:
        audit.record(db, None, "auth.login_failed", "user", user.id if user else None, email)
        db.commit()
        raise AppError(401, "invalid_credentials", "Invalid email or password")
    token, csrf = new_token(), new_token()
    db.add(UserSession(token_hash=hash_token(token), csrf_token=csrf, user_id=user.id, ip=ip,
                       expires_at=utcnow() + timedelta(hours=s.session_hours)))
    user.last_login_at = utcnow()
    audit.record(db, user.id, "auth.login", "user", user.id, user.email)
    db.commit()
    max_age = s.session_hours * 3600
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict", secure=s.cookie_secure,
                        max_age=max_age, path="/")
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, samesite="strict", secure=s.cookie_secure,
                        max_age=max_age, path="/")
    return _me(db, user, {r.role.name for r in user.roles}, csrf)


@router.post("/logout")
def logout(response: Response, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    sess = db.get(UserSession, p.session.id)
    sess.revoked = True
    audit.record(db, p.id, "auth.logout", "user", p.id, p.user.email)
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    p: Principal | None = None
    if token:
        try:
            p = current_principal(request, db)
        except AppError:
            p = None
    if p is None:
        s = get_settings()
        if s.single_operator and s.app_env != "test":
            dev_user = db.execute(select(User).where(User.email == s.dev_email.lower())).scalar_one_or_none()
            if not dev_user:
                dev_user = db.execute(select(User)).scalars().first()
            if dev_user:
                token, csrf = new_token(), new_token()
                host = request.client.host if request.client else "127.0.0.1"
                db.add(UserSession(token_hash=hash_token(token), csrf_token=csrf, user_id=dev_user.id, ip=host,
                                   expires_at=utcnow() + timedelta(hours=s.session_hours)))
                db.commit()
                max_age = s.session_hours * 3600
                response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict", secure=s.cookie_secure,
                                    max_age=max_age, path="/")
                response.set_cookie(CSRF_COOKIE, csrf, httponly=False, samesite="strict", secure=s.cookie_secure,
                                    max_age=max_age, path="/")
                roles = {ur.role.name for ur in dev_user.roles} | {"admin", "qa_engineer", "reviewer"}
                out = _me(db, dev_user, roles, csrf)
                out["project_ids"] = list(db.execute(select(Project.id)).scalars())
                return out
        raise AppError(401, "unauthenticated", "Sign in required")
    out = _me(db, p.user, p.roles, p.session.csrf_token if p.session else "operator-csrf")
    out["project_ids"] = accessible_project_ids(db, p)
    return out
