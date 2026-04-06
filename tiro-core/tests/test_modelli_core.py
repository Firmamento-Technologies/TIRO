import pytest
from sqlalchemy import select
from tiro_core.modelli.core import Soggetto, Flusso, Risorsa


@pytest.mark.asyncio
async def test_crea_soggetto(db_session):
    soggetto = Soggetto(
        tipo="esterno",
        nome="Mario",
        cognome="Rossi",
        email=["mario@example.com"],
        telefono=["+39123456789"],
        ruolo="CEO",
        tag=["cliente"],
        profilo={"settore": "manifattura"},
    )
    db_session.add(soggetto)
    await db_session.commit()
    result = await db_session.execute(select(Soggetto).where(Soggetto.nome == "Mario"))
    s = result.scalar_one()
    assert s.cognome == "Rossi"
    assert s.tipo == "esterno"
    assert "mario@example.com" in s.email
    assert s.profilo["settore"] == "manifattura"


@pytest.mark.asyncio
async def test_crea_flusso_con_soggetto(db_session):
    soggetto = Soggetto(tipo="membro", nome="Luca", cognome="Bianchi", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()
    flusso = Flusso(
        soggetto_id=soggetto.id,
        canale="messaggio",
        direzione="entrata",
        contenuto="Ciao, come procede il progetto?",
        dati_grezzi={"source": "whatsapp", "group": "HALE"},
    )
    db_session.add(flusso)
    await db_session.commit()
    result = await db_session.execute(select(Flusso).where(Flusso.soggetto_id == soggetto.id))
    f = result.scalar_one()
    assert f.canale == "messaggio"
    assert f.direzione == "entrata"
    assert "HALE" in f.dati_grezzi["group"]


@pytest.mark.asyncio
async def test_crea_risorsa(db_session):
    soggetto = Soggetto(tipo="esterno", nome="Anna", cognome="Verdi", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()
    risorsa = Risorsa(
        soggetto_id=soggetto.id,
        origine="allegato",
        titolo="Proposta CFD.pdf",
        contenuto="Contenuto estratto dal PDF...",
        metadati={"pagine": 12, "formato": "pdf"},
    )
    db_session.add(risorsa)
    await db_session.commit()
    result = await db_session.execute(select(Risorsa).where(Risorsa.soggetto_id == soggetto.id))
    r = result.scalar_one()
    assert r.titolo == "Proposta CFD.pdf"
    assert r.metadati["pagine"] == 12
