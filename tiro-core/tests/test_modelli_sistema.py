import pytest
from sqlalchemy import select
from tiro_core.modelli.sistema import Utente, RegolaRischio


@pytest.mark.asyncio
async def test_crea_utente(db_session):
    utente = Utente(
        email="admin@test.com",
        nome="Admin Test",
        password_hash="fakehash123",
        ruolo="titolare",
        perimetro={},
        attivo=True,
    )
    db_session.add(utente)
    await db_session.commit()

    result = await db_session.execute(select(Utente).where(Utente.email == "admin@test.com"))
    u = result.scalar_one()
    assert u.ruolo == "titolare"
    assert u.attivo is True


@pytest.mark.asyncio
async def test_crea_regola_rischio(db_session):
    regola = RegolaRischio(
        pattern_azione="invia_email",
        livello_rischio="medio",
        descrizione="Invio email a contatto esterno",
        approvazione_automatica=False,
    )
    db_session.add(regola)
    await db_session.commit()

    result = await db_session.execute(
        select(RegolaRischio).where(RegolaRischio.pattern_azione == "invia_email")
    )
    r = result.scalar_one()
    assert r.livello_rischio == "medio"
    assert r.approvazione_automatica is False
