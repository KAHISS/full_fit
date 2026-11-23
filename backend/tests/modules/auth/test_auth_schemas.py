from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.modules.auth.schemas import RegisterRequest


def _payload(**overrides):
    data = {
        "nome": "João Silva",
        "email": "joao@example.com",
        "senha": "senha1234",
        "aluno": {},
        "aceite_termos_uso": True,
        "aceite_privacidade": True,
    }
    data.update(overrides)
    return data


def test_minimal_student_registration_is_valid():
    payload = RegisterRequest(**_payload())

    assert payload.aluno is not None
    assert payload.treinador is None
    assert payload.nutricionista is None
    assert payload.aceite_publicidade is False


def test_registration_accepts_several_profiles_at_once():
    payload = RegisterRequest(
        **_payload(aluno={"altura_cm": 180}, treinador={"cref": "012345-G/BA"})
    )

    assert payload.aluno.altura_cm == 180
    assert payload.treinador.cref == "012345-G/BA"


def test_requires_at_least_one_profile():
    with pytest.raises(ValidationError) as exc:
        RegisterRequest(**_payload(aluno=None))

    assert "pelo menos um perfil" in str(exc.value)


def test_password_is_hidden_in_representation():
    payload = RegisterRequest(**_payload(senha="senha1234"))

    assert "senha1234" not in repr(payload)
    assert "senha1234" not in str(payload.model_dump())
    assert payload.senha.get_secret_value() == "senha1234"


def test_password_keeps_surrounding_whitespace():
    payload = RegisterRequest(**_payload(senha="  senha1234  "))

    assert payload.senha.get_secret_value() == "  senha1234  "


def test_text_fields_are_trimmed():
    payload = RegisterRequest(
        **_payload(nome="  João Silva  ", treinador={"cref": "  012345-G/BA "})
    )

    assert payload.nome == "João Silva"
    assert payload.treinador.cref == "012345-G/BA"


def test_email_with_surrounding_whitespace_is_accepted_and_trimmed():
    payload = RegisterRequest(**_payload(email="  joao@example.com "))

    assert payload.email == "joao@example.com"


def test_future_birth_date_is_rejected():
    tomorrow = date.today() + timedelta(days=1)

    with pytest.raises(ValidationError):
        RegisterRequest(**_payload(data_nascimento=tomorrow))


def test_past_birth_date_is_accepted():
    payload = RegisterRequest(**_payload(data_nascimento="2000-05-20"))

    assert payload.data_nascimento == date(2000, 5, 20)


@pytest.mark.parametrize(
    "field, value",
    [
        ("email", "isso-nao-e-email"),
        ("nome", "J"),
        ("apelido", "a" * 31),  # apelido column has 30
        ("telefone", "1" * 21),  # telefone column has 20
        ("treinador", {"cref": "a" * 21}),  # cref column has 20
        ("nutricionista", {"crn": "ab"}),  # minimum is 3
        ("aluno", {"altura_cm": 20}),
        ("aceite_termos_uso", "talvez"),
    ],
)
def test_invalid_fields_are_rejected(field, value):
    with pytest.raises(ValidationError):
        RegisterRequest(**_payload(**{field: value}))


def test_consents_are_required_in_payload():
    data = _payload()
    del data["aceite_termos_uso"]

    with pytest.raises(ValidationError):
        RegisterRequest(**data)
