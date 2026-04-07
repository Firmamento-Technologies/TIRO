"""Schemi Pydantic per il modulo decisionale."""
from datetime import datetime
from pydantic import BaseModel


class PropostaCrea(BaseModel):
    ruolo_agente: str
    tipo_azione: str
    titolo: str
    descrizione: str | None = None
    destinatario: dict = {}


class PropostaResponse(BaseModel):
    id: int
    ruolo_agente: str
    tipo_azione: str
    titolo: str
    descrizione: str | None
    destinatario: dict
    livello_rischio: str
    stato: str
    approvato_da: str | None
    canale_approvazione: str | None
    creato_il: datetime
    deciso_il: datetime | None
    eseguito_il: datetime | None
    model_config = {"from_attributes": True}


class AzioneApprovazione(BaseModel):
    canale: str = "pannello"  # pannello|messaggio|posta


class SessioneResponse(BaseModel):
    id: int
    ciclo: int
    partecipanti: list[str]
    consenso: dict
    conflitti: dict
    creato_il: datetime
    model_config = {"from_attributes": True}
