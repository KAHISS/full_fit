from datetime import date
from typing import Annotated, Self
 
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError
 
# Strips whitespace from both ends. Used only on plain text fields: the password must
# NEVER be altered, otherwise the stored password would differ from the one typed at login.
Trimmed = Annotated[str, StringConstraints(strip_whitespace=True)]
 
 
class StudentRegistration(BaseModel):
    altura_cm: int | None = Field(default=None, ge=50, le=300)
 
 
class TrainerRegistration(BaseModel):
    # Limit of 20 = size of the treinador.cref column.
    cref: Trimmed | None = Field(default=None, min_length=3, max_length=20)
 
 
class NutritionistRegistration(BaseModel):
    # Limit of 20 = size of the nutricionista.crn column.
    crn: Trimmed | None = Field(default=None, min_length=3, max_length=20)
 
 
class RegisterRequest(BaseModel):
    nome: Trimmed = Field(min_length=2, max_length=150)
    email: EmailStr
    senha: SecretStr
    apelido: Trimmed | None = Field(default=None, min_length=1, max_length=30)
    data_nascimento: date | None = None
    telefone: Trimmed | None = Field(default=None, min_length=8, max_length=20)
 
    aluno: StudentRegistration | None = None
    treinador: TrainerRegistration | None = None
    nutricionista: NutritionistRegistration | None = None
 
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
 