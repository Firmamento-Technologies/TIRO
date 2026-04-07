from pydantic import BaseModel


class RegolaRischioResponse(BaseModel):
    id: int
    pattern_azione: str
    livello_rischio: str
    descrizione: str | None
    approvazione_automatica: bool
    model_config = {"from_attributes": True}
