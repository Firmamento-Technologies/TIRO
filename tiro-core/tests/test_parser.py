"""Test per il parser strutturato (regex + NER)."""
import pytest
from tiro_core.elaborazione.parser import (
    estrai_con_regex,
    estrai_firma_email,
    parsa_contenuto,
    DatiEstratti,
)


class TestEstraiConRegex:
    def test_estrae_email(self):
        testo = "Contattatemi a mario@example.com oppure info@firmamento.com"
        risultato = estrai_con_regex(testo)
        assert "mario@example.com" in risultato["email_trovate"]
        assert "info@firmamento.com" in risultato["email_trovate"]

    def test_estrae_telefono(self):
        testo = "Chiamate al +39 333 123 4567 o 06-1234567"
        risultato = estrai_con_regex(testo)
        assert len(risultato["telefoni_trovati"]) >= 1

    def test_estrae_url(self):
        testo = "Visita https://firmamentotechnologies.com per info"
        risultato = estrai_con_regex(testo)
        assert "https://firmamentotechnologies.com" in risultato["url_trovati"]

    def test_estrae_importo_euro(self):
        testo = "Il costo e 1.500 EUR oppure €2.000"
        risultato = estrai_con_regex(testo)
        assert len(risultato["importi_eur"]) >= 1

    def test_estrae_data_italiana(self):
        testo = "Scadenza il 15/04/2026 e consegna il 20.05.2026"
        risultato = estrai_con_regex(testo)
        assert len(risultato["date_menzionate"]) == 2

    def test_estrae_partita_iva(self):
        testo = "P.IVA IT12345678901"
        risultato = estrai_con_regex(testo)
        # Nota: il regex cattura sia con che senza prefisso IT
        assert len(risultato["partite_iva"]) >= 1

    def test_testo_vuoto(self):
        risultato = estrai_con_regex("")
        assert risultato["email_trovate"] == ()
        assert risultato["telefoni_trovati"] == ()


class TestEstraiFirma:
    def test_firma_con_trattini(self):
        testo = "Corpo email\n\n---\nMario Rossi\nCEO Firmamento"
        firma = estrai_firma_email(testo)
        assert "Mario Rossi" in firma
        assert "CEO" in firma

    def test_firma_con_underscore(self):
        testo = "Corpo\n__\nFirma qui"
        firma = estrai_firma_email(testo)
        assert "Firma qui" in firma

    def test_nessuna_firma(self):
        testo = "Email senza firma ne separatori"
        firma = estrai_firma_email(testo)
        assert firma == ""


class TestParsaContenuto:
    def test_parsing_completo(self):
        testo = (
            "Buongiorno, sono Mario Rossi di Firmamento Technologies.\n"
            "Vi scrivo per la proposta da 5.000 EUR.\n"
            "Contattatemi a mario@example.com o al +39 333 1234567.\n"
            "Scadenza: 15/04/2026\n"
            "---\n"
            "Mario Rossi\nCEO\nFirmamento Technologies\nmario@example.com"
        )
        risultato = parsa_contenuto(testo, nlp=None)  # NER skippato senza spaCy
        assert isinstance(risultato, DatiEstratti)
        assert "mario@example.com" in risultato.email_trovate
        assert len(risultato.date_menzionate) >= 1
        assert "Mario Rossi" in risultato.firma_email

    def test_testo_vuoto(self):
        risultato = parsa_contenuto("")
        assert risultato == DatiEstratti()
