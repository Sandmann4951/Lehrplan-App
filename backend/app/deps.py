"""Gemeinsame Abhängigkeiten: angemeldeter Benutzer, Rollenprüfung, CSRF."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .errors import ApiError, forbidden
from .models import ROLE_ADMIN, User, UserSession, utcnow
from .security import hash_token

SESSION_COOKIE = "lp_session"
CSRF_COOKIE = "lp_csrf"
CSRF_HEADER = "X-CSRF-Token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Endpunkte, die bei Passwort-Wechselpflicht weiter erlaubt sind
_PASSWORD_CHANGE_ALLOWED = {"/api/v1/auth/me", "/api/v1/auth/logout", "/api/v1/auth/change-password"}


@dataclass
class Auth:
    user: User
    session: UserSession

    @property
    def is_admin(self) -> bool:
        return self.user.role == ROLE_ADMIN


def _not_authenticated() -> ApiError:
    return ApiError(401, "not_authenticated", "Bitte melden Sie sich an.")


def load_session(db: Session, token: str | None) -> UserSession | None:
    if not token:
        return None
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    if sess is None:
        return None
    if sess.expires_at <= utcnow():
        db.delete(sess)
        db.commit()
        return None
    if not sess.user.active:
        return None
    return sess


def get_auth(request: Request, db: Session = Depends(get_db)) -> Auth:
    sess = load_session(db, request.cookies.get(SESSION_COOKIE))
    if sess is None:
        raise _not_authenticated()
    if request.method in UNSAFE_METHODS:
        header = request.headers.get(CSRF_HEADER)
        if not header or header != sess.csrf_token:
            raise ApiError(403, "csrf_failed", "Sicherheitsprüfung fehlgeschlagen (CSRF). Bitte Seite neu laden.")
    if sess.user.must_change_password and request.url.path not in _PASSWORD_CHANGE_ALLOWED:
        raise ApiError(403, "password_change_required", "Bitte ändern Sie zuerst Ihr Passwort.")
    return Auth(user=sess.user, session=sess)


def require_admin(auth: Auth = Depends(get_auth)) -> Auth:
    if not auth.is_admin:
        raise forbidden()
    return auth


def session_lifetime() -> timedelta:
    return timedelta(hours=settings.session_hours)
