import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.users.models import (
    StatusUsuario,
    StatusVerificacaoPerfil,
    TipoConsentimento,
)
from app.modules.users.service import UserService


def _make_user(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "nome": "João Silva",
        "email": "joao@example.com",
        "status_usuario": StatusUsuario.ATIVO,
        "aluno": None,
        "treinador": None,
        "nutricionista": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def service(repo):
    return UserService(repo)


async def test_get_user_by_id_success(service, repo):
    user = _make_user()
    repo.get_by_id.return_value = user

    result = await service.get_user_by_id(user.id)

    assert result.id == user.id


async def test_get_user_by_id_not_found(service, repo):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.get_user_by_id(uuid.uuid4())


async def test_get_user_by_email_success(service, repo):
    user = _make_user()
    repo.get_by_email.return_value = user

    result = await service.get_user_by_email(user.email)

    assert result.email == user.email


async def test_get_user_by_email_deleted_user_returns_none(service, repo):
    repo.get_by_email.return_value = _make_user(status_usuario=StatusUsuario.EXCLUIDO)

    result = await service.get_user_by_email("joao@example.com")

    assert result is None


async def test_create_account_success(service, repo):
    user = _make_user()
    repo.email_exists.return_value = False
    repo.create_user.return_value = user
    repo.get_by_id.return_value = user
    consents = [
        (TipoConsentimento.TERMOS_USO, True, "1.0"),
        (TipoConsentimento.PRIVACIDADE, True, "1.0"),
    ]

    result = await service.create_account(
        nome="João",
        email="joao@example.com",
        senha_hash="hash",
        consents=consents,
        ip="127.0.0.1",
    )

    assert result.id == user.id
    repo.record_consents.assert_awaited_once()


async def test_create_account_duplicate_email_error(service, repo):
    repo.email_exists.return_value = True

    with pytest.raises(ConflictError):
        await service.create_account(
            nome="João",
            email="joao@example.com",
            senha_hash="hash",
            consents=[],
            ip="127.0.0.1",
        )


async def test_update_profile_success(service, repo):
    user = _make_user()
    repo.get_by_id.return_value = user

    result = await service.update_profile(user.id, user_fields={"nome": "Novo Nome"})

    assert result.id == user.id
    repo.update_user_data.assert_awaited_once_with(user, {"nome": "Novo Nome"})


async def test_update_profile_without_student_profile_error(service, repo):
    user = _make_user(aluno=None)
    repo.get_by_id.return_value = user

    with pytest.raises(BadRequestError):
        await service.update_profile(
            user.id, user_fields={}, altura_cm=180, update_altura_cm=True
        )


async def test_activate_student_profile_success(service, repo):
    user = _make_user(aluno=None)
    repo.get_by_id.return_value = user

    await service.activate_student_profile(user.id, altura_cm=175)

    repo.create_student_profile.assert_awaited_once_with(user_id=user.id, altura_cm=175)


async def test_activate_student_profile_already_exists_error(service, repo):
    user = _make_user(aluno=SimpleNamespace(altura_cm=175))
    repo.get_by_id.return_value = user

    with pytest.raises(ConflictError):
        await service.activate_student_profile(user.id)


async def test_activate_trainer_profile_success(service, repo):
    user = _make_user(treinador=None)
    repo.get_by_id.return_value = user

    await service.activate_trainer_profile(user.id, cref="123456-G/SP")

    repo.create_trainer_profile.assert_awaited_once_with(
        user_id=user.id, cref="123456-G/SP"
    )


async def test_activate_trainer_profile_already_exists_error(service, repo):
    user = _make_user(treinador=SimpleNamespace(cref="123456-G/SP"))
    repo.get_by_id.return_value = user

    with pytest.raises(ConflictError):
        await service.activate_trainer_profile(user.id)


async def test_activate_nutritionist_profile_success(service, repo):
    user = _make_user(nutricionista=None)
    repo.get_by_id.return_value = user

    await service.activate_nutritionist_profile(user.id, crn="12345")

    repo.create_nutritionist_profile.assert_awaited_once_with(
        user_id=user.id, crn="12345"
    )


async def test_activate_nutritionist_profile_already_exists_error(service, repo):
    user = _make_user(nutricionista=SimpleNamespace(crn="12345"))
    repo.get_by_id.return_value = user

    with pytest.raises(ConflictError):
        await service.activate_nutritionist_profile(user.id)


async def test_update_professional_verification_status_success(service, repo):
    user_id = uuid.uuid4()

    await service.update_professional_verification_status(
        user_id,
        profile_type="CREF",
        status=StatusVerificacaoPerfil.APROVADO,
        registry_number="123456-G/SP",
    )

    repo.update_trainer_status.assert_awaited_once()


async def test_update_professional_verification_status_invalid_type_error(
    service, repo
):
    with pytest.raises(BadRequestError):
        await service.update_professional_verification_status(
            uuid.uuid4(),
            profile_type="INVALIDO",
            status=StatusVerificacaoPerfil.APROVADO,
        )


async def test_record_login_failure_success(service, repo):
    user_id = uuid.uuid4()

    await service.record_login_failure(user_id, 1, None)

    repo.record_login_failure.assert_awaited_once_with(
        user_id=user_id, failed_attempts=1, locked_until=None
    )


async def test_record_login_failure_repo_error(service, repo):
    repo.record_login_failure.side_effect = RuntimeError("db error")

    with pytest.raises(RuntimeError):
        await service.record_login_failure(uuid.uuid4(), 1, None)


async def test_record_login_success_success(service, repo):
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    await service.record_login_success(user_id, now)

    repo.record_login_success.assert_awaited_once_with(user_id=user_id, last_login=now)


async def test_record_login_success_repo_error(service, repo):
    repo.record_login_success.side_effect = RuntimeError("db error")

    with pytest.raises(RuntimeError):
        await service.record_login_success(uuid.uuid4(), datetime.now(timezone.utc))


async def test_confirm_user_email_success(service, repo):
    user_id = uuid.uuid4()

    await service.confirm_user_email(user_id)

    repo.verify_email.assert_awaited_once_with(user_id=user_id)


async def test_confirm_user_email_repo_error(service, repo):
    repo.verify_email.side_effect = RuntimeError("db error")

    with pytest.raises(RuntimeError):
        await service.confirm_user_email(uuid.uuid4())


async def test_change_password_success(service, repo):
    user_id = uuid.uuid4()

    await service.change_password(user_id, "new_hash")

    repo.update_password.assert_awaited_once_with(
        user_id=user_id, new_password_hash="new_hash"
    )


async def test_change_password_repo_error(service, repo):
    repo.update_password.side_effect = RuntimeError("db error")

    with pytest.raises(RuntimeError):
        await service.change_password(uuid.uuid4(), "new_hash")


async def test_delete_account_success(service, repo):
    user = _make_user()
    repo.get_by_id.return_value = user

    await service.delete_account(user.id)

    repo.update_user_data.assert_awaited_once()
    updated_data = repo.update_user_data.call_args.args[1]
    assert updated_data["status_usuario"] == StatusUsuario.EXCLUIDO


async def test_delete_account_not_found_error(service, repo):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.delete_account(uuid.uuid4())
