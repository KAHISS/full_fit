# Decisões de projeto

Registro das decisões que não são óbvias pelo código. Cada decisão tem um status:
**Aprovada**, **Proposta** (aguardando confirmação) ou **Substituída**.

## Índice

| # | Área | Decisão | Status |
|---|------|---------|--------|
| D-01 | Banco | PostgreSQL gerenciado com Alembic | Aprovada |
| D-02 | Banco | Fonte de verdade do schema | Aprovada |
| D-03 | Banco | Modelo conceitual cobre só a v1.0 (sem nutrição) | Aprovada |
| D-04 | Banco | Chaves primárias em UUID | Proposta |
| D-05 | Banco | Perfis como especialização de Usuário | Proposta |
| D-06 | Banco | Planilha em uma única tabela, com tipo | Aprovada |
| D-07 | Banco | Atribuir planilha cria uma cópia | Aprovada |
| D-08 | Banco | Treino livre sem divisão nem planilha | Aprovada |
| D-09 | Banco | Exercícios padrão, personalizados e inativação | Aprovada |
| D-10 | Banco | Verificação de profissionais com histórico | Aprovada |
| D-11 | Banco | Bloqueio de login na aplicação, sem tabela | Aprovada |
| D-12 | Banco | Tokens persistidos apenas como hash | Aprovada |
| D-13 | Banco | Consentimento versionado e auditoria imutável | Aprovada |
| D-14 | Banco | Tipos de dados no PostgreSQL | Proposta |

## Banco de dados

### D-01 PostgreSQL gerenciado com Alembic
O domínio é fortemente relacional (vínculos, planilhas, treinos, assinaturas) e várias regras viram constraints do banco. O Mongo foi modelado antes e descartado. Banco gerenciado para ter backup e restauração sem operar servidor. Migrações versionadas com Alembic.

### D-02 Fonte de verdade do schema
Os models do SQLAlchemy e as migrações do Alembic são a fonte de verdade. O diagrama conceitual (`docs/banco/`) documenta o porquê do modelo e pode ficar desatualizado. Em caso de divergência, vale o código.

### D-03 Escopo do modelo conceitual
O modelo cobre os módulos de acesso, treinos e verificação de profissionais. Vínculo, chat, financeiro e anúncios entram no diagrama antes das sprints correspondentes. Nutrição fica fora da v1.0.

### D-04 Chaves primárias em UUID
UUID em todas as tabelas. O app gera o id das tabelas criadas offline (treino, série), o que torna a sincronização idempotente (upsert pelo próprio id), sem coluna `id_cliente` separada.

### D-05 Perfis como especialização de Usuário
Aluno, Treinador e Nutricionista especializam Usuário. O administrador é a flag `permissao_admin`, não um perfil. Cada perfil vira uma tabela.

### D-06 Planilha em uma única tabela, com tipo
A tabela `Planilha` cobre três casos, diferenciados por `tipo_planilha`:

| Tipo | Criador | `id_aluno` | `id_origem` |
|------|---------|-----------|-------------|
| MODELO | Treinador | nulo | nulo |
| ATRIBUIDA | Treinador | aluno | modelo de origem |
| PROPRIA | o próprio aluno | o próprio aluno | nulo |

- O criador (`id_criador`) aponta para Usuário, não para Treinador, para permitir a planilha própria do aluno.
- As combinações acima são garantidas por CHECK no banco.
- Só uma planilha ativa por aluno: índice único parcial `UNIQUE (id_aluno) WHERE status = 'ATIVA'`.
- As limitações do aluno (só exercícios padrão, limite de planilhas) são regra de negócio, lidas da configuração de planos, e não ficam no schema.

### D-07 Atribuir planilha cria uma cópia
Atribuir copia planilha, divisões e itens para o aluno, ativa a cópia e move a anterior para o histórico, tudo em uma transação. `id_origem` liga a cópia ao modelo. Treinos já feitos apontam para o exercício (não para o item da planilha), então editar ou trocar a planilha não altera o histórico.

### D-08 Treino livre
`Treino.id_divisao` é opcional. Um treino sem divisão é um treino livre, sem planilha.

### D-09 Exercícios padrão, personalizados e inativação
- Exercício padrão não tem criador (`id_criador` nulo); o personalizado aponta para o treinador autor.
- Exercício em uso nunca é apagado, só inativado (`ativo = false`), para não quebrar planilhas e treinos.
- Equipamento é opcional (vazio significa peso corporal). Todo exercício tem ao menos um grupo muscular.

### D-10 Verificação de profissionais com histórico
Cada envio de documento gera uma linha em `Verificacao_Profissional`, o que preserva reenvios após rejeição.
- Só uma verificação `PENDENTE` por profissional (índice único parcial).
- Rejeitada exige `motivo_rejeicao`; decidida exige avaliador e data (CHECK).
- `status_verificacao` no perfil do profissional é o estado atual, atualizado na mesma transação da decisão, para a busca não consultar o histórico.
- O documento fica em armazenamento privado; só se guarda o caminho.

### D-11 Bloqueio de login na aplicação
Sem tabela de tentativas de login. Bloqueio por conta com `falhas_login` e `bloqueado_ate` em Usuário (bloqueios curtos e crescentes, para evitar que terceiros tranquem a conta de alguém). Limite por IP via rate limiting na aplicação ou no hosting. Reavaliar com Redis se houver mais de uma instância da API.

### D-12 Tokens persistidos apenas como hash
`Token_Usuario` (verificação de e-mail e recuperação de senha, uso único e expiração) e `Refresh_Token` (com revogação) guardam só o hash, nunca o valor. Há rotação com detecção de reuso com o campo `id_substituido_por` 

### D-13 Consentimento versionado e auditoria imutável
`Consentimento` guarda `versao_documento` e `ip` para provar qual texto foi aceito e permitir novo aceite quando o texto mudar. `Auditoria` só recebe inserções e permite autor nulo (ações do sistema).

### D-14 Tipos de dados no PostgreSQL
- Datas e horas: `timestamptz`.
- `senha_hash`: `TEXT` (hash argon2 passa de 90 caracteres).
- `email`: único e sem distinção de maiúsculas (`citext` ou `lower()`).
- `ip`: `inet`.
- Registro profissional (CREF/CRN): texto, não inteiro.
