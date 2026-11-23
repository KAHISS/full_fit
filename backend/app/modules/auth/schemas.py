from datetime import date
from typing import Annotated, Any, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    EmailStr,
    Field,
    SecretStr,
    StringConstraints,
    field_validator,
    model_validator,
    AfterValidator,
)
from pydantic_core import PydanticCustomError


def _blank_to_none(value: Any) -> Any:
    """Trata string vazia ou só com espaços como "não informada"."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


# Remove espaços das pontas. Usado só em campos de texto comum: a senha NUNCA pode ser
# alterada, senão a senha cadastrada seria diferente da digitada no login.
Trimmed = Annotated[str, StringConstraints(strip_whitespace=True)]

# Campos opcionais: "" (o que um campo de formulário em branco costuma enviar) vira None.
OptionalTrimmed = Annotated[Trimmed | None, BeforeValidator(_blank_to_none)]
OptionalDate = Annotated[date | None, BeforeValidator(_blank_to_none)]
OptionalInt = Annotated[int | None, BeforeValidator(_blank_to_none)]

# E-mails são guardados e comparados em minúsculas (índice único em lower(email)), então
# o login precisa enxergar o mesmo valor que o cadastro gravou.
LowercaseEmail = Annotated[EmailStr, AfterValidator(str.lower)]


class StudentRegistration(BaseModel):
    altura_cm: OptionalInt = Field(default=None, ge=50, le=300)


class TrainerRegistration(BaseModel):
    # Limite de 20 = tamanho da coluna treinador.cref.
    cref: OptionalTrimmed = Field(default=None, min_length=3, max_length=20)


class NutritionistRegistration(BaseModel):
    # Limite de 20 = tamanho da coluna nutricionista.crn.
    crn: OptionalTrimmed = Field(default=None, min_length=3, max_length=20)


class RegisterRequest(BaseModel):
    nome: Trimmed = Field(min_length=2, max_length=150)
    email: LowercaseEmail
    # SecretStr esconde a senha em repr, logs e tracebacks. As regras de tamanho e
    # composição ficam em security.validate_password_strength (configuradas pelo .env).
    senha: SecretStr
    apelido: OptionalTrimmed = Field(default=None, min_length=1, max_length=30)
    data_nascimento: OptionalDate = None
    telefone: OptionalTrimmed = Field(default=None, min_length=8, max_length=20)

    # Perfis: envie o bloco de cada perfil que a pessoa quer criar. Um bloco vazio
    # (por exemplo "aluno": {}) cria o perfil sem dados extras.
    aluno: StudentRegistration | None = None
    treinador: TrainerRegistration | None = None
    nutricionista: NutritionistRegistration | None = None

    # Termos e privacidade são obrigatórios: False é rejeitado aqui (400 com o nome do campo
    # em `extra`). Publicidade é opcional, e o False dela ainda é registrado como consentimento.
    aceite_termos_uso: bool
    aceite_privacidade: bool
    aceite_publicidade: bool = False

    @field_validator("data_nascimento")
    @classmethod
    def birth_date_cannot_be_in_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise PydanticCustomError(
                "birth_date_in_future", "A data de nascimento não pode estar no futuro."
            )
        return value

    @model_validator(mode="after")
    def require_at_least_one_profile(self) -> Self:
        if self.aluno is None and self.treinador is None and self.nutricionista is None:
            raise PydanticCustomError(
                "profile_required",
                "Escolha pelo menos um perfil: aluno, treinador ou nutricionista.",
            )
        return self

    @field_validator("aceite_termos_uso", "aceite_privacidade")
    @classmethod
    def must_accept(cls, value: bool) -> bool:
        if not value:
            raise PydanticCustomError(
                "consent_required", "É necessário aceitar para criar a conta."
            )
        return value
