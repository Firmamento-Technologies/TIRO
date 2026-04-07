from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    tipo: str = "bearer"


class UtenteResponse(BaseModel):
    id: int
    email: str
    nome: str
    ruolo: str
    perimetro: dict
    attivo: bool
    model_config = {"from_attributes": True}
