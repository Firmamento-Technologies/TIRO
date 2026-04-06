import pytest
from sqlalchemy import select
from tiro_core.modelli.commerciale import Ente, Opportunita, Fascicolo
from tiro_core.modelli.core import Soggetto


@pytest.mark.asyncio
async def test_crea_ente_e_opportunita(db_session):
    ente = Ente(nome="UniGe", settore="accademia", dimensione="grande", profilo={})
    db_session.add(ente)
    await db_session.commit()

    soggetto = Soggetto(tipo="esterno", nome="Prof", cognome="Rossi", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    opp = Opportunita(
        ente_id=ente.id,
        soggetto_id=soggetto.id,
        titolo="Consulenza CFD",
        fase="proposta",
        valore_eur=15000.0,
        probabilita=0.7,
        dettagli={"tipo": "consulenza"},
    )
    db_session.add(opp)
    await db_session.commit()

    result = await db_session.execute(select(Opportunita).where(Opportunita.ente_id == ente.id))
    o = result.scalar_one()
    assert o.titolo == "Consulenza CFD"
    assert o.fase == "proposta"
    assert o.valore_eur == 15000.0


@pytest.mark.asyncio
async def test_crea_fascicolo(db_session):
    soggetto = Soggetto(tipo="esterno", nome="Test", cognome="Fascicolo", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    fascicolo = Fascicolo(
        soggetto_id=soggetto.id,
        sintesi="Cliente attivo.",
        indice_rischio=0.2,
        indice_opportunita=0.8,
        sezioni={"storia": "..."},
    )
    db_session.add(fascicolo)
    await db_session.commit()

    result = await db_session.execute(
        select(Fascicolo).where(Fascicolo.soggetto_id == soggetto.id)
    )
    f = result.scalar_one()
    assert f.indice_rischio == 0.2
    assert f.indice_opportunita == 0.8
