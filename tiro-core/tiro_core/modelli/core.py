from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from tiro_core.database import Base


class Soggetto(Base):
    __tablename__ = "soggetti"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))
    nome: Mapped[str] = mapped_column(String(100))
    cognome: Mapped[str] = mapped_column(String(100))
    email: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    telefono: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    organizzazione_id: Mapped[int | None] = mapped_column(nullable=True)
    ruolo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tag: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    profilo: Mapped[dict] = mapped_column(JSONB, default=dict)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    aggiornato_il: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    flussi: Mapped[list["Flusso"]] = relationship(back_populates="soggetto")
    risorse: Mapped[list["Risorsa"]] = relationship(back_populates="soggetto")


class Flusso(Base):
    __tablename__ = "flussi"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(primary_key=True)
    soggetto_id: Mapped[int] = mapped_column(ForeignKey("core.soggetti.id"))
    canale: Mapped[str] = mapped_column(String(20))
    direzione: Mapped[str] = mapped_column(String(10))
    oggetto: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contenuto: Mapped[str | None] = mapped_column(Text, nullable=True)
    dati_grezzi: Mapped[dict] = mapped_column(JSONB, default=dict)
    vettore = mapped_column(Vector(1536), nullable=True)
    ricevuto_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    elaborato_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    soggetto: Mapped["Soggetto"] = relationship(back_populates="flussi")


class Risorsa(Base):
    __tablename__ = "risorse"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(primary_key=True)
    soggetto_id: Mapped[int | None] = mapped_column(ForeignKey("core.soggetti.id"), nullable=True)
    origine: Mapped[str] = mapped_column(String(20))
    titolo: Mapped[str] = mapped_column(String(500))
    contenuto: Mapped[str | None] = mapped_column(Text, nullable=True)
    vettore = mapped_column(Vector(1536), nullable=True)
    metadati: Mapped[dict] = mapped_column(JSONB, default=dict)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    soggetto: Mapped["Soggetto | None"] = relationship(back_populates="risorse")
