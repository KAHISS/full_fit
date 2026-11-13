import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TipoConselho(StrEnum):
    CREF = "CREF"
    CRN = "CRN"


class StatusVerificacao(StrEnum):
    PENDENTE = "PENDENTE"
    APROVADA = "APROVADA"
    REJEITADA = "REJEITADA"


class VerificacaoProfissional(Base):
    __tablename__ = "verificacao_profissional"
    __table_args__ = (
        CheckConstraint(
            "tipo_conselho IN ('CREF', 'CRN')", name="tipo_conselho_valido"
        ),
        CheckConstraint(
            "status IN ('PENDENTE', 'APROVADA', 'REJEITADA')", name="status_valido"
        ),
        CheckConstraint(
            "status <> 'REJEITADA' OR (motivo_rejeicao IS NOT NULL AND LENGTH(TRIM(motivo_rejeicao)) > 0)",
            name="rejeitada_motivo",
        ),
        CheckConstraint(
            "status = 'PENDENTE' OR (id_avaliador IS NOT NULL AND avaliado_em IS NOT NULL)",
            name="decidida_avaliador",
        ),
        Index(
            "uq_verificacao_pendente_por_profissional",
            "id_usuario",
            "tipo_conselho",
            unique=True,
            postgresql_where=text("status = 'PENDENTE'"),
        ),
        Index(
            "uq_registro_profissional_aprovado",
            "tipo_conselho",
            "numero_registro",
            "uf",
            unique=True,
            postgresql_where=text("status = 'APROVADA'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    id_avaliador: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
    )
    tipo_conselho: Mapped[str] = mapped_column(Text, nullable=False)
    numero_registro: Mapped[str] = mapped_column(Text, nullable=False)
    uf: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    documento_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=StatusVerificacao.PENDENTE,
        server_default=text("'PENDENTE'"),
    )
    motivo_rejeicao: Mapped[str | None] = mapped_column(Text)
    enviado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    avaliado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
