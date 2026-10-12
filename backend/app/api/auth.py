"""F01 Anmeldung und Konten."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..audit import audit
from ..config import settings
from ..db import get_db
from ..deps import CSRF_COOKIE, SESSION_COOKIE, Auth, get_auth, session_lifetime
from ..errors import ApiError, invalid
from ..models import LoginAttempt, UserSession, utcnow
from ..repositories.core import UserRepository
from ..schemas import ChangePasswordIn, LoginIn
from ..security import DUMMY_HASH, hash_password, hash_token, new_token, password_problem, verify_password
from ..serializers import user_out

router = APIRouter(prefix="/auth", tags=["Anmeldung"])


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_cookies(response: Response, token: str, csrf: str) -> None:
    max_age = int(session_lifetime().total_seconds())
    response.set_cookie(SESSION_COOKIE, token, max_age=max_age, httponly=True, samesite="lax", secure=settings.cookie_secure, path="/")
    response.set_cookie(CSRF_COOKIE, csrf, max_age=max_age, httponly=False, samesite="lax", secure=settings.cookie_secure, path="/")


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


@router.post("/login", summary="Anmelden")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = client_ip(request)
    window_start = utcnow() - timedelta(minutes=settings.login_window_minutes)
    failures = db.scalar(
        select(func.count()).select_from(LoginAttempt).where(
            LoginAttempt.email == body.email,
            LoginAttempt.ip == ip,
            LoginAttempt.success.is_(False),
            LoginAttempt.attempted_at >= window_start,
        )
    ) or 0
    if failures >= settings.login_max_failures:
        raise ApiError(429, "too_many_attempts", f"Zu viele Fehlversuche. Bitte versuchen Sie es in {settings.login_window_minutes} Minuten erneut.")

    user = UserRepository(db).by_email(body.email)
    ok = verify_password(user.password_hash if user else DUMMY_HASH, body.password)
    if not user or not ok or not user.active:
        db.add(LoginAttempt(email=body.email, ip=ip, success=False))
        db.commit()
        raise ApiError(401, "invalid_credentials", "E-Mail oder Passwort ist falsch, oder das Konto ist gesperrt.")

    # Abgelaufene Sitzungen und alte Versuche aufräumen
    db.execute(delete(UserSession).where(UserSession.expires_at <= utcnow()))
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < utcnow() - timedelta(days=1)))
    token, csrf = new_token(), new_token()
    db.add(UserSession(user_id=user.id, token_hash=hash_token(token), csrf_token=csrf, expires_at=utcnow() + session_lifetime()))
    db.add(LoginAttempt(email=body.email, ip=ip, success=True))
    audit(db, user.id, "login", "user", user.id)
    db.commit()
    _set_cookies(response, token, csrf)
    return {"user": user_out(user), "csrf_token": csrf}


@router.post("/logout", summary="Abmelden")
def logout(response: Response, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    sess = db.get(UserSession, auth.session.id)
    if sess:
        db.delete(sess)
    audit(db, auth.user.id, "logout", "user", auth.user.id)
    db.commit()
    _clear_cookies(response)
    return {"ok": True}


@router.get("/me", summary="Aktuelle Sitzung prüfen")
def me(auth: Auth = Depends(get_auth)):
    return {"user": user_out(auth.user), "csrf_token": auth.session.csrf_token, "expires_at": auth.session.expires_at.isoformat()}


@router.post("/change-password", summary="Passwort wechseln")
def change_password(body: ChangePasswordIn, response: Response, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    user = auth.user
    if not verify_password(user.password_hash, body.current_password):
        raise invalid("Das aktuelle Passwort ist falsch.", {"current_password": "Falsches Passwort."})
    problem = password_problem(body.new_password)
    if problem:
        raise invalid("Das neue Passwort ist zu schwach.", {"new_password": problem})
    if body.new_password == body.current_password:
        raise invalid("Das neue Passwort muss sich unterscheiden.", {"new_password": "Bitte ein anderes Passwort wählen."})
    user = db.merge(user)
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.version += 1
    # Alle anderen Sitzungen beenden
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.id != auth.session.id))
    audit(db, user.id, "password_changed", "user", user.id)
    db.commit()
    return {"user": user_out(user)}
