import uuid
from datetime import UTC, datetime, timedelta
 
import jwt
import pytest
 
from app.config import settings
from app.core.exceptions import BadRequestError, UnauthorizedError
from app.modules.auth.security import (
    create_access_token,
    decode_access_token,
    email_verification_token_ttl,
    generate_opaque_token,
    hash_password,
    hash_token,
    issue_opaque_token,
    password_reset_token_ttl,
    refresh_token_ttl,
    validate_password_strength,
    verify_password,
)
 
# ---------------------------------------------------------------- senha
 
 
def test_hash_password_nao_guarda_senha_em_texto_puro():
    hashed = hash_password("senha123")
 
    assert hashed != "senha123"
    assert hashed.startswith("$argon2")
 
 
def test_hash_password_usa_salt_diferente_a_cada_chamada():
    assert hash_password("senha123") != hash_password("senha123")
 
 
def test_verify_password_aceita_senha_correta():
    hashed = hash_password("senha123")
 
    assert verify_password("senha123", hashed) is True
 
 
def test_verify_password_rejeita_senha_errada():
    hashed = hash_password("senha123")
 
    assert verify_password("outra456", hashed) is False
 
 
@pytest.mark.parametrize("senha", ["abc12345", "Senha1234", "a" * 127 + "1"])
def test_validate_password_strength_aceita_senhas_validas(senha):
    validate_password_strength(senha)
 
 
@pytest.mark.parametrize(
    "senha",
    [
        "abc123",  # curta demais
        "somenteletras",  # sem número
        "1234567890",  # sem letra
        "a1" * 65,  # 130 caracteres, longa demais
    ],
)
def test_validate_password_strength_rejeita_senhas_fracas(senha):
    with pytest.raises(BadRequestError) as exc:
        validate_password_strength(senha)
 
    assert exc.value.code == "senha_fraca"
 
 
# ---------------------------------------------------------- access token
 
 
def test_access_token_ida_e_volta_devolve_o_mesmo_usuario():
    user_id = uuid.uuid4()
 
    token = create_access_token(user_id)
 
    assert decode_access_token(token) == user_id
 
 
def test_access_token_expirado_lanca_token_expirado(monkeypatch):
    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)
    token = create_access_token(uuid.uuid4())
 
    with pytest.raises(UnauthorizedError) as exc:
        decode_access_token(token)
 
    assert exc.value.code == "token_expirado"
 
 
def test_access_token_com_assinatura_de_outra_chave_e_rejeitado():
    agora = datetime.now(UTC)
    forjado = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "iat": agora,
            "exp": agora + timedelta(minutes=5),
        },
        "x" * 40,
        algorithm=settings.jwt_algorithm,
    )
 
    with pytest.raises(UnauthorizedError) as exc:
        decode_access_token(forjado)
 
    assert exc.value.code == "token_invalido"
 
 
def test_token_de_outro_tipo_nao_vale_como_access():
    agora = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "refresh",
            "iat": agora,
            "exp": agora + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
 
    with pytest.raises(UnauthorizedError) as exc:
        decode_access_token(token)
 
    assert exc.value.code == "token_invalido"
 
 
def test_token_sem_sub_e_rejeitado():
    agora = datetime.now(UTC)
    token = jwt.encode(
        {"type": "access", "iat": agora, "exp": agora + timedelta(minutes=5)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
 
    with pytest.raises(UnauthorizedError):
        decode_access_token(token)
 
 
def test_token_com_sub_que_nao_e_uuid_e_rejeitado():
    agora = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "nao-e-uuid",
            "type": "access",
            "iat": agora,
            "exp": agora + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
 
    with pytest.raises(UnauthorizedError):
        decode_access_token(token)
 
 
@pytest.mark.parametrize("lixo", ["", "abc", "a.b.c"])
def test_texto_qualquer_nao_e_um_access_token(lixo):
    with pytest.raises(UnauthorizedError) as exc:
        decode_access_token(lixo)
 
    assert exc.value.code == "token_invalido"
 
 
# ----------------------------------------------------------- tokens opacos
 
 
def test_generate_opaque_token_e_unico():
    assert len({generate_opaque_token() for _ in range(100)}) == 100
 
 
def test_hash_token_e_deterministico_e_nao_revela_o_token():
    token = generate_opaque_token()
 
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token
    assert len(hash_token(token)) == 64
 
 
def test_hash_token_difere_para_tokens_diferentes():
    assert hash_token("a") != hash_token("b")
 
 
def test_issue_opaque_token_entrega_valor_hash_e_expiracao():
    antes = datetime.now(UTC)
 
    emitido = issue_opaque_token(password_reset_token_ttl())
 
    assert emitido.hash == hash_token(emitido.value)
    assert emitido.value != emitido.hash
    assert antes + password_reset_token_ttl() <= emitido.expires_at
    assert emitido.expires_at <= datetime.now(UTC) + password_reset_token_ttl()
 
 
def test_ttls_vem_das_configuracoes(monkeypatch):
    monkeypatch.setattr(settings, "refresh_token_expire_days", 7)
    monkeypatch.setattr(settings, "email_verification_token_expire_hours", 2)
    monkeypatch.setattr(settings, "password_reset_token_expire_minutes", 10)
 
    assert refresh_token_ttl() == timedelta(days=7)
    assert email_verification_token_ttl() == timedelta(hours=2)
    assert password_reset_token_ttl() == timedelta(minutes=10)
 
 
def test_limites_de_senha_vem_das_configuracoes(monkeypatch):
    monkeypatch.setattr(settings, "password_min_length", 12)
    monkeypatch.setattr(settings, "password_max_length", 20)
 
    validate_password_strength("abcdefghij12")  # 12 caracteres: ok
 
    with pytest.raises(BadRequestError) as curta:
        validate_password_strength("abcdefghi12")  # 11 caracteres
    with pytest.raises(BadRequestError) as longa:
        validate_password_strength("a" * 20 + "1")  # 21 caracteres
 
    assert "12" in curta.value.detail
    assert "20" in longa.value.detail
 
 
def test_config_rejeita_minimo_maior_que_maximo(monkeypatch):
    from app.config import Settings
 
    with pytest.raises(ValueError):
        Settings(password_min_length=30, password_max_length=10)
 