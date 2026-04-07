from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tiro_core.config import settings
from tiro_core.database import get_db
from tiro_core.modelli.sistema import Utente

security = HTTPBearer()


async def get_utente_corrente(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Utente:
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        utente_id: int = int(sub)
        if utente_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    result = await db.execute(select(Utente).where(Utente.id == utente_id))
    utente = result.scalar_one_or_none()
    if utente is None or not utente.attivo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return utente


def richiedi_ruolo(*ruoli: str):
    async def verificatore(utente: Utente = Depends(get_utente_corrente)):
        if utente.ruolo not in ruoli:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permesso insufficiente")
        return utente
    return verificatore
