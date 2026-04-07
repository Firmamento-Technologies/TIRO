from datetime import datetime, timedelta, timezone
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


def crea_token(utente_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(utente_id), "exp": expire}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/login", response_model=TokenResponse)
async def login(dati: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Utente).where(Utente.email == dati.email))
    utente = result.scalar_one_or_none()
    if utente is None or not pwd_context.verify(dati.password, utente.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide")
    if not utente.attivo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Utente disattivato")
    token = crea_token(utente.id)
    return TokenResponse(access_token=token)
