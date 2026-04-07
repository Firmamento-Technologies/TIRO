from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tiro_core.api.dipendenze import get_utente_corrente
from tiro_core.database import get_db
from tiro_core.modelli.sistema import Utente

router = APIRouter(prefix="/ricerca", tags=["ricerca"])


class RicercaRequest(BaseModel):
    vettore: list[float]
    limite: int = 10
    tabella: str = "flussi"


class RisultatoRicerca(BaseModel):
    id: int
    contenuto: str | None
    distanza: float


@router.post("", response_model=list[RisultatoRicerca])
async def ricerca_semantica(
    dati: RicercaRequest,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    schema_tabella = {"flussi": "core.flussi", "risorse": "core.risorse"}
    tabella = schema_tabella.get(dati.tabella)
    if tabella is None:
        return []
    result = await db.execute(
        text(
            f"SELECT id, contenuto, vettore <-> :qv AS distanza "
            f"FROM {tabella} WHERE vettore IS NOT NULL "
            f"ORDER BY vettore <-> :qv LIMIT :limite"
        ),
        {"qv": str(dati.vettore), "limite": dati.limite},
    )
    return [
        RisultatoRicerca(id=row.id, contenuto=row.contenuto, distanza=row.distanza)
        for row in result.all()
    ]
