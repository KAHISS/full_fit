import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.users.models import StatusUsuario, StatusVerificacaoPerfil


class StudentHealthConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    descricao: str


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    altura_cm: int | None
    condicoes_saude: list[StudentHealthConditionResponse]


class TrainerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cref: str | None
    status_verificacao: StatusVerificacaoPerfil


class NutritionistProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    crn: str | None
    status_verificacao: StatusVerificacaoPerfil


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    apelido: str | None
    email: EmailStr
    data_nascimento: date | None
    telefone: str | None
    biografia: str | None
    foto_url: str | None
    status_usuario: StatusUsuario
    email_verificado: bool
    ultimo_login: datetime | None
    criado_em: datetime
    atualizado_em: datetime
    aluno: StudentProfileResponse | None
    treinador: TrainerProfileResponse | None
    nutricionista: NutritionistProfileResponse | None


class PublicTrainerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cref: str | None
    status_verificacao: StatusVerificacaoPerfil


class PublicNutritionistProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    crn: str | None
    status_verificacao: StatusVerificacaoPerfil


class PublicUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    apelido: str | None
    biografia: str | None
    foto_url: str | None
    treinador: PublicTrainerProfileResponse | None
    nutricionista: PublicNutritionistProfileResponse | None


class UpdateProfileRequest(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    apelido: str | None = Field(default=None, max_length=80)
    data_nascimento: date | None = None
    telefone: str | None = Field(default=None, max_length=20)
    biografia: str | None = Field(default=None, max_length=1000)
    foto_url: str | None = Field(default=None, max_length=500)
    altura_cm: int | None = Field(default=None, ge=50, le=300)
    condicoes_saude: list[str] | None = None


class ActivateStudentProfileRequest(BaseModel):
    altura_cm: int | None = Field(default=None, ge=50, le=300)


class ActivateTrainerProfileRequest(BaseModel):
    cref: str | None = Field(default=None, min_length=3, max_length=30)


class ActivateNutritionistProfileRequest(BaseModel):
    crn: str | None = Field(default=None, min_length=3, max_length=30)