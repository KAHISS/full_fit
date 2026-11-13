import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.users.models import (
    Aluno,
    AlunoCondicaoSaude,
    Consentimento,
    Nutricionista,
    StatusUsuario,
    StatusVerificacaoPerfil,
    TipoConsentimento,
    Treinador,
    Usuario,
)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(
        self,
        *,
        nome: str,
        email: str,
        senha_hash: str,
        apelido: str | None = None,
        data_nascimento: date | None = None,
        telefone: str | None = None,
        biografia: str | None = None,
        foto_url: str | None = None,
    ) -> Usuario:
        user = Usuario(
            nome=nome,
            apelido=apelido,
            email=email,
            senha_hash=senha_hash,
            data_nascimento=data_nascimento,
            telefone=telefone,
            biografia=biografia,
            foto_url=foto_url,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(
        self, user_id: uuid.UUID, *, load_profiles: bool = False
    ) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.id == user_id)
        if load_profiles:
            stmt = stmt.options(
                selectinload(Usuario.aluno).selectinload(Aluno.condicoes_saude),
                selectinload(Usuario.treinador),
                selectinload(Usuario.nutricionista),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(
        self, email: str, *, load_profiles: bool = False
    ) -> Usuario | None:
        stmt = select(Usuario).where(func.lower(Usuario.email) == email.strip().lower())
        if load_profiles:
            stmt = stmt.options(
                selectinload(Usuario.aluno).selectinload(Aluno.condicoes_saude),
                selectinload(Usuario.treinador),
                selectinload(Usuario.nutricionista),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        stmt = select(Usuario.id).where(
            func.lower(Usuario.email) == email.strip().lower()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update_user_data(self, user: Usuario, data: dict[str, Any]) -> Usuario:
        for field, value in data.items():
            setattr(user, field, value)
        await self.session.flush()
        return user

    async def record_login_failure(
        self,
        user_id: uuid.UUID,
        failed_attempts: int,
        locked_until: datetime | None,
    ) -> None:
        stmt = (
            update(Usuario)
            .where(Usuario.id == user_id)
            .values(falhas_login=failed_attempts, bloqueado_ate=locked_until)
        )
        await self.session.execute(stmt)

    async def record_login_success(
        self, user_id: uuid.UUID, last_login: datetime
    ) -> None:
        stmt = (
            update(Usuario)
            .where(Usuario.id == user_id)
            .values(
                falhas_login=0,
                bloqueado_ate=None,
                ultimo_login=last_login,
            )
        )
        await self.session.execute(stmt)

    async def verify_email(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(Usuario)
            .where(Usuario.id == user_id)
            .values(
                email_verificado=True,
                status_usuario=StatusUsuario.ATIVO,
            )
        )
        await self.session.execute(stmt)

    async def update_password(self, user_id: uuid.UUID, new_password_hash: str) -> None:
        stmt = (
            update(Usuario)
            .where(Usuario.id == user_id)
            .values(
                senha_hash=new_password_hash,
                falhas_login=0,
                bloqueado_ate=None,
            )
        )
        await self.session.execute(stmt)

    async def update_status(self, user_id: uuid.UUID, status: StatusUsuario) -> None:
        stmt = (
            update(Usuario).where(Usuario.id == user_id).values(status_usuario=status)
        )
        await self.session.execute(stmt)

    async def create_student_profile(
        self, user_id: uuid.UUID, altura_cm: int | None = None
    ) -> Aluno:
        student = Aluno(id_usuario=user_id, altura_cm=altura_cm)
        self.session.add(student)
        await self.session.flush()
        return student

    async def replace_student_health_conditions(
        self, student_id: uuid.UUID, descriptions: list[str]
    ) -> list[AlunoCondicaoSaude]:
        await self.session.execute(
            delete(AlunoCondicaoSaude).where(AlunoCondicaoSaude.id_aluno == student_id)
        )
        new_conditions = [
            AlunoCondicaoSaude(id_aluno=student_id, descricao=description)
            for description in descriptions
        ]
        if new_conditions:
            self.session.add_all(new_conditions)
            await self.session.flush()
        return new_conditions

    async def create_trainer_profile(
        self, user_id: uuid.UUID, cref: str | None = None
    ) -> Treinador:
        trainer = Treinador(id_usuario=user_id, cref=cref)
        self.session.add(trainer)
        await self.session.flush()
        return trainer

    async def update_trainer_status(
        self,
        user_id: uuid.UUID,
        verification_status: StatusVerificacaoPerfil,
        cref: str | None = None,
    ) -> None:
        values: dict[str, Any] = {"status_verificacao": verification_status}
        if cref is not None:
            values["cref"] = cref
        stmt = update(Treinador).where(Treinador.id_usuario == user_id).values(**values)
        await self.session.execute(stmt)

    async def create_nutritionist_profile(
        self, user_id: uuid.UUID, crn: str | None = None
    ) -> Nutricionista:
        nutritionist = Nutricionista(id_usuario=user_id, crn=crn)
        self.session.add(nutritionist)
        await self.session.flush()
        return nutritionist

    async def update_nutritionist_status(
        self,
        user_id: uuid.UUID,
        verification_status: StatusVerificacaoPerfil,
        crn: str | None = None,
    ) -> None:
        values: dict[str, Any] = {"status_verificacao": verification_status}
        if crn is not None:
            values["crn"] = crn
        stmt = (
            update(Nutricionista)
            .where(Nutricionista.id_usuario == user_id)
            .values(**values)
        )
        await self.session.execute(stmt)

    async def record_consents(
        self,
        user_id: uuid.UUID,
        consents: list[tuple[TipoConsentimento, bool, str]],
        ip: str,
    ) -> list[Consentimento]:
        records = [
            Consentimento(
                id_usuario=user_id,
                tipo=consent_type,
                aceito=accepted,
                versao_documento=document_version,
                ip=ip,
            )
            for consent_type, accepted, document_version in consents
        ]
        self.session.add_all(records)
        await self.session.flush()
        return records
