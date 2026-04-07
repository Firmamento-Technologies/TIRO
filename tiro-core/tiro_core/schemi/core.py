from datetime import datetime
from pydantic import BaseModel


class SoggettoCrea(BaseModel):
    tipo: str
    nome: str
    cognome: str
    email: list[str] = []
    telefono: list[str] = []
    organizzazione_id: int | None = None
    ruolo: str | None = None
    tag: list[str] = []
    profilo: dict = {}


class SoggettoAggiorna(BaseModel):
    tipo: str | None = None
    nome: str | None = None
    cognome: str | None = None
    email: list[str] | None = None
    telefono: list[str] | None = None
    ruolo: str | None = None
    tag: list[str] | None = None
    profilo: dict | None = None


class SoggettoResponse(BaseModel):
    id: int
    tipo: str
    nome: str
    cognome: str
    email: list[str]
    telefono: list[str]
    organizzazione_id: int | None
    ruolo: str | None
    tag: list[str]
    profilo: dict
    creato_il: datetime
    aggiornato_il: datetime
    model_config = {"from_attributes": True}


class FlussoResponse(BaseModel):
    id: int
    soggetto_id: int
    canale: str
    direzione: str
    oggetto: str | None
    contenuto: str | None
    dati_grezzi: dict
    ricevuto_il: datetime
    elaborato_il: datetime | None
    model_config = {"from_attributes": True}
