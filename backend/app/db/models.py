from app.modules.admin.models import Auditoria
from app.modules.auth.models import RefreshToken, TokenUsuario
from app.modules.catalogs.models import (
    AlunoObjetivo,
    Equipamento,
    Especialidade,
    GrupoMuscular,
    ObjetivoTreino,
    ProfissionalEspecialidade,
)
from app.modules.users.models import (
    Aluno,
    AlunoCondicaoSaude,
    Consentimento,
    Nutricionista,
    Treinador,
    Usuario,
)
from app.modules.verification.models import VerificacaoProfissional

__all__ = [
    "Aluno",
    "AlunoCondicaoSaude",
    "AlunoObjetivo",
    "Auditoria",
    "Consentimento",
    "Equipamento",
    "Especialidade",
    "GrupoMuscular",
    "Nutricionista",
    "ObjetivoTreino",
    "ProfissionalEspecialidade",
    "RefreshToken",
    "TokenUsuario",
    "Treinador",
    "Usuario",
    "VerificacaoProfissional",
]