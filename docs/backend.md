# FullFit — Documentação Técnica do Backend

Este documento resume a arquitetura, pilha de tecnologias e **lista de comandos de referência rápida** para o desenvolvimento e operação do backend da aplicação **FullFit**.

---

## 🛠️ Stack Tecnológica

* **Linguagem / Runtime:** Python 3.14
* **Gerenciador de Pacotes e Ambiente:** [uv](https://github.com/astral-sh/uv)
* **Framework Web:** FastAPI (com Uvicorn)
* **Banco de Dados:** PostgreSQL 17 (assíncrono via `asyncpg`)
* **ORM:** SQLAlchemy 2.0 (modo `asyncio`)
* **Migrações de Banco:** Alembic (modo assíncrono)
* **Containerização:** Docker & Docker Compose

---

## 📁 Estrutura de Pastas do Backend

```text
backend/
├── alembic/                # Arquivos de migração do banco
│   ├── versions/           # Scripts de migração gerados
│   └── env.py              # Configuração assíncrona do Alembic
├── app/
│   ├── main.py             # Ponto de entrada FastAPI (create_app)
│   ├── config.py           # Configurações globais (pydantic-settings)
│   ├── db/
│   │   └── base.py         # Declarative Base e importação de Models
│   └── modules/            # Módulos da aplicação (auth, users, admin, etc.)
├── tests/                  # Testes automatizados (pytest)
├── compose.yaml            # Configuração dos serviços Docker (API + Postgres)
├── compose.test.yaml       # Banco PostgreSQL isolado para testes
├── Dockerfile              # Imagem Docker multi-stage da API
├── pyproject.toml          # Dependências do projeto (uv)
└── .env                    # Variáveis de ambiente locais (não versionado)
```

---

## ⚡ Guia Rápido de Comandos

> **Atenção:** Certifique-se de executar os comandos a partir da pasta `backend/`.

### 1. 🐋 Gerenciamento do Ambiente Docker

#### Subir os containers de desenvolvimento (API + Postgres)
```powershell
docker compose up -d --build
```

#### Parar os containers
```powershell
docker compose down
```

#### Parar e remover volumes do banco de dados (Reset completo do banco)
```powershell
docker compose down -v
```

#### Ver status dos containers
```powershell
docker compose ps
```

#### Acompanhar os logs da aplicação em tempo real
```powershell
docker compose logs -f api
```

---

### 2. 🗄️ Migrações de Banco de Dados (Alembic via Docker)

Sempre que alterar ou criar um novo modelo SQLAlchemy em `app/modules/`, utilize os comandos abaixo **com os containers rodando**.

#### Criar uma nova migração (autogerada)
```powershell
docker compose exec api alembic revision --autogenerate -m "descricao_da_migracao"
```

#### Aplicar migrações pendentes no banco
```powershell
docker compose exec api alembic upgrade head
```

#### Reverter a última migração aplicada (Downgrade)
```powershell
docker compose exec api alembic downgrade -1
```

#### Ver histórico de migrações
```powershell
docker compose exec api alembic history
```

#### Ver migração atual aplicada no banco
```powershell
docker compose exec api alembic current
```

---

### 3. 💻 Desenvolvimento Local sem Docker (via `uv`)

Caso opte por rodar a API diretamente na sua máquina hospedeira:

#### Instalar / Sincronizar dependências do ambiente virtual
```powershell
uv sync
```

#### Subir o servidor de desenvolvimento FastAPI
```powershell
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Gerar e aplicar migrações localmente (requer Postgres local ou exposto no localhost:5432)
```powershell
uv run alembic revision --autogenerate -m "nome_da_migracao"
uv run alembic upgrade head
```

#### Gerar chave JWT segura (para o `.env`)
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

### 4. 🧪 Testes e Qualidade de Código

#### Subir o banco de dados de testes isolado (Porta 5433)
```powershell
docker compose -f compose.test.yaml up -d db-test
```

#### Executar a suíte de testes com `pytest`
```powershell
uv run pytest
```

#### Executar linter e checagem de código com `ruff`
```powershell
uv run ruff check .
```

#### Corrigir problemas de linting automaticamente
```powershell
uv run ruff check --fix .
```

---

## 🔑 Variáveis de Ambiente (`.env`)

Exemplo de configuração para o arquivo `.env` na raiz da pasta `backend`:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://fullfit:fullfit@localhost:5432/fullfit
TEST_DATABASE_URL=postgresql+asyncpg://fullfit:fullfit@localhost:5433/fullfit_test
JWT_SECRET_KEY=sua_chave_secreta_com_no_minimo_32_caracteres
```

> **Nota:** Quando a API roda dentro do Docker Compose, a variável `DATABASE_URL` é automaticamente sobrescrita para conectar no container do banco (`db:5432`).