from datetime import datetime, date
from sqlalchemy import DateTime, Date, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from tiro_core.database import Base


class Ente(Base):
    __tablename__ = "enti"
    __table_args__ = {"schema": "commerciale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    settore: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dimensione: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sito: Mapped[str | None] = mapped_column(String(300), nullable=True)
    profilo: Mapped[dict] = mapped_column(JSONB, default=dict)

    opportunita: Mapped[list["Opportunita"]] = relationship(back_populates="ente")
    fascicoli: Mapped[list["Fascicolo"]] = relationship(back_populates="ente")


class Opportunita(Base):
    __tablename__ = "opportunita"
    __table_args__ = {"schema": "commerciale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ente_id: Mapped[int | None] = mapped_column(ForeignKey("commerciale.enti.id"), nullable=True)
    soggetto_id: Mapped[int | None] = mapped_column(ForeignKey("core.soggetti.id"), nullable=True)
    titolo: Mapped[str] = mapped_column(String(300))
    fase: Mapped[str] = mapped_column(String(30))
    valore_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    probabilita: Mapped[float | None] = mapped_column(Float, nullable=True)
    chiusura_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    dettagli: Mapped[dict] = mapped_column(JSONB, default=dict)

    ente: Mapped["Ente | None"] = relationship(back_populates="opportunita")


class Interazione(Base):
    __tablename__ = "interazioni"
    __table_args__ = {"schema": "commerciale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunita_id: Mapped[int | None] = mapped_column(ForeignKey("commerciale.opportunita.id"), nullable=True)
    soggetto_id: Mapped[int | None] = mapped_column(ForeignKey("core.soggetti.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(50))
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    pianificato_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completato_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Fascicolo(Base):
    __tablename__ = "fascicoli"
    __table_args__ = {"schema": "commerciale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    soggetto_id: Mapped[int | None] = mapped_column(ForeignKey("core.soggetti.id"), nullable=True)
    ente_id: Mapped[int | None] = mapped_column(ForeignKey("commerciale.enti.id"), nullable=True)
    sintesi: Mapped[str | None] = mapped_column(Text, nullable=True)
    indice_rischio: Mapped[float | None] = mapped_column(Float, nullable=True)
    indice_opportunita: Mapped[float | None] = mapped_column(Float, nullable=True)
    generato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sezioni: Mapped[dict] = mapped_column(JSONB, default=dict)

    ente: Mapped["Ente | None"] = relationship(back_populates="fascicoli")
