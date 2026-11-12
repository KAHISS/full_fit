import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AcaoAuditoria(StrEnum):
    VERIFICACAO_APROVADA = "VERIFICACAO_APROVADA"
    VERIFICACAO_REJEITADA = "VERIFICACAO_REJEITADA"
    CONTA_EXCLUIDA = "CONTA_EXCLUIDA"


class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        CheckConstraint(
            "acao IN ('VERIFICACAO_APROVADA', 'VERIFICACAO_REJEITADA', 'CONTA_EXCLUIDA')",
            name="acao_valida",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    id_usuario: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
    )
    acao: Mapped[str] = mapped_column(Text, nullable=False)
    entidade: Mapped[str] = mapped_column(Text, nullable=False)
    id_entidade: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    detalhes: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(INET)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )