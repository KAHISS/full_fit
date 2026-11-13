import uuid
from datetime import date, datetime
from typing import Any

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
)
from app.modules.users.models import (
    StatusUsuario,
    StatusVerificacaoPerfil,
    TipoConsentimento,
    Usuario,
)
from app.modules.users.repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def get_user_by_id(
        self, user_id: uuid.UUID, *, load_profiles: bool = True
    ) -> Usuario:
        user = await self.repository.get_by_id(user_id, load_profiles=load_profiles)
        if not user or user.status_usuario == StatusUsuario.EXCLUIDO:
            raise NotFoundError(
                detail="Usuário não encontrado.",
                code="usuario_nao_encontrado",
            )
        return user

    async def get_user_by_email(
        self, email: str, *, load_profiles: bool = True
    ) -> Usuario | None:
        user = await self.repository.get_by_email(email, load_profiles=load_profiles)
        if user and user.status_usuario == StatusUsuario.EXCLUIDO:
            return None
        return user

    async def create_account(
        self,
        *,
        nome: str,
        email: str,
        senha_hash: str,
        consents: list[tuple[TipoConsentimento, bool, str]],
        ip: str,
        apelido: str | None = None,
        data_nascimento: date | None = None,
        telefone: str | None = None,
        biografia: str | None = None,
        foto_url: str | None = None,
        create_student: bool = False,
        altura_cm: int | None = None,
        create_trainer: bool = False,
        cref: str | None = None,
        create_nutritionist: bool = False,
        crn: str | None = None,
    ) -> Usuario:
        normalized_email = email.strip().lower()
        if await self.repository.email_exists(normalized_email):
            raise ConflictError(
                detail="Já existe uma conta cadastrada com este e-mail.",
                code="email_ja_cadastrado",
            )

        self._validate_required_consents(consents)

        user = await self.repository.create_user(
            nome=nome.strip(),
            email=normalized_email,
            senha_hash=senha_hash,
            apelido=apelido.strip() if apelido else None,
            data_nascimento=data_nascimento,
            telefone=telefone.strip() if telefone else None,
            biografia=biografia,
            foto_url=foto_url,
        )

        if create_student:
            await self.repository.create_student_profile(
                user_id=user.id, altura_cm=altura_cm
            )

        if create_trainer:
            await self.repository.create_trainer_profile(user_id=user.id, cref=cref)

        if create_nutritionist:
            await self.repository.create_nutritionist_profile(user_id=user.id, crn=crn)

        await self.repository.record_consents(
            user_id=user.id,
            consents=consents,
            ip=ip,
        )

        return await self.get_user_by_id(user.id, load_profiles=True)

    async def update_profile(
        self,
        user_id: uuid.UUID,
        *,
        user_fields: dict[str, Any],
        altura_cm: int | None = None,
        update_altura_cm: bool = False,
        condicoes_saude: list[str] | None = None,
    ) -> Usuario:
        user = await self.get_user_by_id(user_id, load_profiles=True)

        allowed_fields = {
            "nome",
            "apelido",
            "data_nascimento",
            "telefone",
            "biografia",
            "foto_url",
        }
        sanitized_data = {
            key: value for key, value in user_fields.items() if key in allowed_fields
        }

        if sanitized_data:
            await self.repository.update_user_data(user, sanitized_data)

        if update_altura_cm or condicoes_saude is not None:
            if not user.aluno:
                raise BadRequestError(
                    detail="O usuário não possui perfil de aluno ativo.",
                    code="perfil_aluno_nao_encontrado",
                )

            if update_altura_cm:
                user.aluno.altura_cm = altura_cm

            if condicoes_saude is not None:
                cleaned_conditions = [
                    item.strip() for item in condicoes_saude if item.strip()
                ]
                await self.repository.replace_student_health_conditions(
                    student_id=user.id,
                    descriptions=cleaned_conditions,
                )

        return await self.get_user_by_id(user.id, load_profiles=True)

    async def activate_student_profile(
        self, user_id: uuid.UUID, *, altura_cm: int | None = None
    ) -> Usuario:
        user = await self.get_user_by_id(user_id, load_profiles=True)
        if user.aluno:
            raise ConflictError(
                detail="O perfil de aluno já está ativo para este usuário.",
                code="perfil_ja_existente",
            )

        await self.repository.create_student_profile(
            user_id=user.id, altura_cm=altura_cm
        )
        return await self.get_user_by_id(user.id, load_profiles=True)

    async def activate_trainer_profile(
        self, user_id: uuid.UUID, *, cref: str | None = None
    ) -> Usuario:
        user = await self.get_user_by_id(user_id, load_profiles=True)
        if user.treinador:
            raise ConflictError(
                detail="O perfil de treinador já está ativo para este usuário.",
                code="perfil_ja_existente",
            )

        await self.repository.create_trainer_profile(user_id=user.id, cref=cref)
        return await self.get_user_by_id(user.id, load_profiles=True)

    async def activate_nutritionist_profile(
        self, user_id: uuid.UUID, *, crn: str | None = None
    ) -> Usuario:
        user = await self.get_user_by_id(user_id, load_profiles=True)
        if user.nutricionista:
            raise ConflictError(
                detail="O perfil de nutricionista já está ativo para este usuário.",
                code="perfil_ja_existente",
            )

        await self.repository.create_nutritionist_profile(user_id=user.id, crn=crn)
        return await self.get_user_by_id(user.id, load_profiles=True)

    async def update_professional_verification_status(
        self,
        user_id: uuid.UUID,
        *,
        profile_type: str,
        status: StatusVerificacaoPerfil,
        registry_number: str | None = None,
    ) -> None:
        if profile_type == "CREF":
            await self.repository.update_trainer_status(
                user_id=user_id,
                verification_status=status,
                cref=registry_number,
            )
        elif profile_type == "CRN":
            await self.repository.update_nutritionist_status(
                user_id=user_id,
                verification_status=status,
                crn=registry_number,
            )
        else:
            raise BadRequestError(
                detail="Tipo de perfil profissional inválido.",
                code="tipo_perfil_invalido",
            )

    async def record_login_failure(
        self,
        user_id: uuid.UUID,
        failed_attempts: int,
        locked_until: datetime | None,
    ) -> None:
        await self.repository.record_login_failure(
            user_id=user_id,
            failed_attempts=failed_attempts,
            locked_until=locked_until,
        )

    async def record_login_success(
        self, user_id: uuid.UUID, last_login: datetime
    ) -> None:
        await self.repository.record_login_success(
            user_id=user_id, last_login=last_login
        )

    async def confirm_user_email(self, user_id: uuid.UUID) -> None:
        await self.repository.verify_email(user_id=user_id)

    async def change_password(self, user_id: uuid.UUID, new_password_hash: str) -> None:
        await self.repository.update_password(
            user_id=user_id, new_password_hash=new_password_hash
        )

    async def delete_account(self, user_id: uuid.UUID) -> None:
        user = await self.get_user_by_id(user_id, load_profiles=False)
        anonymized_email = f"deleted_{user.id}@deleted.local"
        await self.repository.update_user_data(
            user,
            {
                "nome": "Usuário Excluído",
                "apelido": None,
                "email": anonymized_email,
                "senha_hash": "DELETED",
                "data_nascimento": None,
                "telefone": None,
                "biografia": None,
                "foto_url": None,
                "status_usuario": StatusUsuario.EXCLUIDO,
            },
        )

    @staticmethod
    def _validate_required_consents(
        consents: list[tuple[TipoConsentimento, bool, str]],
    ) -> None:
        accepted_types = {
            consent_type for consent_type, accepted, _ in consents if accepted
        }
        required = {TipoConsentimento.TERMOS_USO, TipoConsentimento.PRIVACIDADE}
        if not required.issubset(accepted_types):
            raise BadRequestError(
                detail="O aceite dos Termos de Uso e da Política de Privacidade é obrigatório.",
                code="consentimentos_obrigatorios_ausentes",
            )
