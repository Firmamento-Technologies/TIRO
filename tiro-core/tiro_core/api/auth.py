from collections import defaultdict
from datetime import datetime, timedelta, timezone
from time import time

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tiro_core.config import settings
from tiro_core.database import get_db
from tiro_core.modelli.sistema import Utente
from tiro_core.schemi.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Lazy-initialized dummy hash for constant-time user enumeration protection.
# Initialized on first login request to avoid module-load-time bcrypt issues.
_DUMMY_HASH: str | None = None


def _get_dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = pwd_context.hash("dummy")
    return _DUMMY_HASH


# In-memory rate limiter: email -> list of attempt timestamps
_login_attempts: dict[str, list[float]] = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60


def _check_rate_limit(email: str) -> None:
    now = time()
    # Prune old attempts outside the window
    _login_attempts[email] = [t for t in _login_attempts[email] if now - t < WINDOW_SECONDS]
    if len(_login_attempts[email]) >= MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Troppi tentativi. Riprova tra un minuto.",
        )
    _login_attempts[email].append(now)


def crea_token(utente_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(utente_id), "exp": expire}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/login", response_model=TokenResponse)
async def login(dati: LoginRequest, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(dati.email)
    result = await db.execute(select(Utente).where(Utente.email == dati.email))
    utente = result.scalar_one_or_none()
    if utente is None:
        # Always run bcrypt to prevent timing-based user enumeration
        pwd_context.verify(dati.password, _get_dummy_hash())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide")
    if not pwd_context.verify(dati.password, utente.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide")
    if not utente.attivo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Utente disattivato")
    token = crea_token(utente.id)
    return TokenResponse(access_token=token)
