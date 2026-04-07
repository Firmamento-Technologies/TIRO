from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from tiro_core.database import Base


class Task(Base):
    __tablename__ = "task"
    __table_args__ = {"schema": "operativo"}

    id: Mapped[int] = mapped_column(primary_key=True)
    titolo: Mapped[str] = mapped_column(String(300))
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    stato: Mapped[str] = mapped_column(String(20), default="aperta")  # aperta/in_corso/completata/annullata
    priorita: Mapped[str] = mapped_column(String(10), default="media")  # bassa/media/alta/urgente
    assegnato_a: Mapped[int | None] = mapped_column(ForeignKey("sistema.utenti.id"), nullable=True)
    soggetto_id: Mapped[int | None] = mapped_column(ForeignKey("core.soggetti.id"), nullable=True)
    origine: Mapped[str | None] = mapped_column(String(50), nullable=True)  # manuale/agente/pipeline
    scadenza: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dettagli: Mapped[dict] = mapped_column(JSONB, default=dict)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completato_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
