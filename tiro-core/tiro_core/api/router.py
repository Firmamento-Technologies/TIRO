from fastapi import APIRouter
from tiro_core.api import auth, soggetti, flussi, opportunita, fascicoli, proposte, ricerca, sistema

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(soggetti.router)
api_router.include_router(flussi.router)
api_router.include_router(opportunita.router)
api_router.include_router(fascicoli.router)
api_router.include_router(proposte.router)
api_router.include_router(ricerca.router)
api_router.include_router(sistema.router)
