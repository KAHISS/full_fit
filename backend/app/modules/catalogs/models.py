import uuid
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TipoProfissional(StrEnum):
    TREINADOR = "TREINADOR"
    NUTRICIONISTA = "NUTRICIONISTA"


class GrupoMuscular(Base):
    __tablename__ = "grupo_muscular"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    nome: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)


class Equipamento(Base):
    __tablename__ = "equipamento"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    nome: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)


class ObjetivoTreino(Base):
    __tablename__ = "objetivo_treino"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    nome: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)


class Especialidade(Base):
    __tablename__ = "especialidade"
    __table_args__ = (
        CheckConstraint(
            "tipo_profissional IN ('TREINADOR', 'NUTRICIONISTA')",
            name="tipo_profissional_valido",
        ),
        UniqueConstraint("nome", "tipo_profissional"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    tipo_profissional: Mapped[str] = mapped_column(Text, nullable=False)


class ProfissionalEspecialidade(Base):
    __tablename__ = "profissional_especialidade"

    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        primary_key=True,
    )
    id_especialidade: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("especialidade.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class AlunoObjetivo(Base):
    __tablename__ = "aluno_objetivo"

    id_aluno: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aluno.id_usuario", ondelete="CASCADE"),
        primary_key=True,
    )
    id_objetivo_treino: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("objetivo_treino.id", ondelete="RESTRICT"),
        primary_key=True,
    )
