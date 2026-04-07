from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tiro_core.api.dipendenze import get_utente_corrente
from tiro_core.database import get_db
from tiro_core.modelli.operativo import Task
from tiro_core.modelli.sistema import Utente

router = APIRouter(prefix="/task", tags=["operativo"])


class TaskCrea(BaseModel):
    titolo: str
    descrizione: str | None = None
    priorita: str = "media"
    assegnato_a: int | None = None
    soggetto_id: int | None = None
    origine: str = "manuale"


class TaskResponse(BaseModel):
    id: int
    titolo: str
    descrizione: str | None
    stato: str
    priorita: str
    assegnato_a: int | None
    soggetto_id: int | None
    origine: str | None
    creato_il: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj: Task) -> "TaskResponse":
        return cls(
            id=obj.id,
            titolo=obj.titolo,
            descrizione=obj.descrizione,
            stato=obj.stato,
            priorita=obj.priorita,
            assegnato_a=obj.assegnato_a,
            soggetto_id=obj.soggetto_id,
            origine=obj.origine,
            creato_il=str(obj.creato_il),
        )


@router.get("", response_model=list[TaskResponse])
async def lista_task(
    stato: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    query = select(Task).order_by(Task.creato_il.desc()).limit(limit).offset(offset)
    if stato:
        query = query.where(Task.stato == stato)
    result = await db.execute(query)
    tasks = result.scalars().all()
    return [TaskResponse.from_orm(t) for t in tasks]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def crea_task(
    dati: TaskCrea,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    task = Task(**dati.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return TaskResponse.from_orm(task)
