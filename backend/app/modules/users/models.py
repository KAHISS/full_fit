import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class StatusUsuario(StrEnum):
    PENDENTE_EMAIL = "PENDENTE_EMAIL"
    ATIVO = "ATIVO"
    SUSPENSO = "SUSPENSO"
    EXCLUIDO = "EXCLUIDO"


class StatusVerificacaoPerfil(StrEnum):
    NAO_ENVIADO = "NAO_ENVIADO"
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    REJEITADO = "REJEITADO"


class TipoConsentimento(StrEnum):
    TERMOS_USO = "TERMOS_USO"
    PRIVACIDADE = "PRIVACIDADE"
    PUBLICIDADE = "PUBLICIDADE"


class Usuario(TimestampMixin, Base):
    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint(
            "status_usuario IN ('PENDENTE_EMAIL', 'ATIVO', 'SUSPENSO', 'EXCLUIDO')",
            name="status_usuario_valido",
        ),
        Index("uq_usuario_email_lower", func.lower(text("email")), unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    apelido: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    senha_hash: Mapped[str] = mapped_column(Text, nullable=False)
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    telefone: Mapped[str | None] = mapped_column(String(20))
    biografia: Mapped[str | None] = mapped_column(Text)
    foto_url: Mapped[str | None] = mapped_column(Text)
    email_verificado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    status_usuario: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=StatusUsuario.PENDENTE_EMAIL,
        server_default=text("'PENDENTE_EMAIL'"),
    )
    permissao_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    falhas_login: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    aluno: Mapped[Aluno | None] = relationship(
        back_populates="usuario", uselist=False, cascade="all, delete-orphan"
    )
    treinador: Mapped[Treinador | None] = relationship(
        back_populates="usuario", uselist=False, cascade="all, delete-orphan"
    )
    nutricionista: Mapped[Nutricionista | None] = relationship(
        back_populates="usuario", uselist=False, cascade="all, delete-orphan"
    )
    consentimentos: Mapped[list[Consentimento]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )


class Aluno(Base):
    __tablename__ = "aluno"

    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        primary_key=True,
    )
    altura_cm: Mapped[int | None] = mapped_column(Integer)

    usuario: Mapped[Usuario] = relationship(back_populates="aluno")
    condicoes_saude: Mapped[list[AlunoCondicaoSaude]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )


class AlunoCondicaoSaude(Base):
    __tablename__ = "aluno_condicao_saude"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    id_aluno: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aluno.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)

    aluno: Mapped[Aluno] = relationship(back_populates="condicoes_saude")


class Treinador(Base):
    __tablename__ = "treinador"
    __table_args__ = (
        CheckConstraint(
            "status_verificacao IN ('NAO_ENVIADO', 'PENDENTE', 'APROVADO', 'REJEITADO')",
            name="status_verificacao_valido",
        ),
    )

    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cref: Mapped[str | None] = mapped_column(String(20))
    status_verificacao: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=StatusVerificacaoPerfil.NAO_ENVIADO,
        server_default=text("'NAO_ENVIADO'"),
    )

    usuario: Mapped[Usuario] = relationship(back_populates="treinador")


class Nutricionista(Base):
    __tablename__ = "nutricionista"
    __table_args__ = (
        CheckConstraint(
            "status_verificacao IN ('NAO_ENVIADO', 'PENDENTE', 'APROVADO', 'REJEITADO')",
            name="status_verificacao_valido",
        ),
    )

    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        primary_key=True,
    )
    crn: Mapped[str | None] = mapped_column(String(20))
    status_verificacao: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=StatusVerificacaoPerfil.NAO_ENVIADO,
        server_default=text("'NAO_ENVIADO'"),
    )

    usuario: Mapped[Usuario] = relationship(back_populates="nutricionista")


class Consentimento(Base):
    __tablename__ = "consentimento"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('TERMOS_USO', 'PRIVACIDADE', 'PUBLICIDADE')",
            name="tipo_valido",
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
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    aceito: Mapped[bool] = mapped_column(Boolean, nullable=False)
    versao_documento: Mapped[str] = mapped_column(String(10), nullable=False)
    ip: Mapped[str] = mapped_column(INET, nullable=False)
    registrado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    usuario: Mapped[Usuario] = relationship(back_populates="consentimentos")
