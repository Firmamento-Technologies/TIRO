from datetime import datetime, date
from pydantic import BaseModel


class OpportunitaCrea(BaseModel):
    ente_id: int | None = None
    soggetto_id: int | None = None
    titolo: str
    fase: str = "contatto"
    valore_eur: float | None = None
    probabilita: float | None = None
    chiusura_prevista: date | None = None
    dettagli: dict = {}


class OpportunitaResponse(BaseModel):
    id: int
    ente_id: int | None
    soggetto_id: int | None
    titolo: str
    fase: str
    valore_eur: float | None
    probabilita: float | None
    chiusura_prevista: date | None
    dettagli: dict
    model_config = {"from_attributes": True}


class FascicoloResponse(BaseModel):
    id: int
    soggetto_id: int | None
    ente_id: int | None
    sintesi: str | None
    indice_rischio: float | None
    indice_opportunita: float | None
    generato_il: datetime
    sezioni: dict
    model_config = {"from_attributes": True}
