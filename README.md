# Checkflow

Backend para definição e execução de fluxos de validação em sistemas distribuídos.
Um plano agrupa steps ordenados; cada step executa uma chamada HTTP e avalia seus
asserts. As execuções são assíncronas e orientadas a eventos.

## Arquitetura

O backend usa uma única imagem e o Honcho inicia os processos do `Procfile`:

- `api`: CRUD e solicitação de execuções em FastAPI;
- `scheduler`: transforma eventos agendados em solicitações de execução;
- `dispatcher`: consome solicitações do Kafka e cria tasks no Celery;
- `celery`: executa os steps em background;
- `realtime`: transmite o stream de progresso por WebSocket e recebe comandos.

Kafka funciona como event bus no tópico `checkflow.execution-events`. Grupos de
consumidores independentes recebem o mesmo stream. Redis é usado como cache do
último estado de cada execução e como broker/backend do Celery. PostgreSQL armazena
planos, steps, histórico das execuções e resultados de cada chamada.

O serviço one-shot `kafka-init` cria o tópico antes de liberar o backend.

## Subindo o ambiente

Pré-requisitos: Docker com Compose.

```bash
cp .env.example .env
docker compose up --build
```

O container `backend` aplica `alembic upgrade head` e executa `honcho start`.

Serviços disponíveis:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- WebSocket: `ws://localhost:8001/ws/plans/{plan_id}/executions`

Para encerrar:

```bash
docker compose down
```

Adicione `-v` somente quando também quiser apagar os dados locais.

## Desenvolvimento local

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
docker compose up -d postgres redis kafka
.venv/bin/alembic upgrade head
.venv/bin/honcho start
```

Para executar a API no host, ajuste `DATABASE_URL` para um PostgreSQL acessível
fora da rede do Compose. O caminho recomendado para subir o stack inteiro é o
comando `docker compose up --build` da seção anterior.

## API

### Planos

```text
POST   /plans
GET    /plans
GET    /plans/{plan_id}
PUT    /plans/{plan_id}
DELETE /plans/{plan_id}
```

### Steps

```text
POST   /plans/{plan_id}/steps
GET    /plans/{plan_id}/steps
GET    /plans/{plan_id}/steps/{step_id}
PUT    /plans/{plan_id}/steps/{step_id}
DELETE /plans/{plan_id}/steps/{step_id}
PATCH  /plans/{plan_id}/steps/reorder
POST   /plans/{plan_id}/executions
GET    /plans/{plan_id}/executions
GET    /plans/{plan_id}/executions/{execution_id}
POST   /plans/{plan_id}/executions/{execution_id}/cancel
POST   /plans/{plan_id}/executions/{execution_id}/retry
```

Exemplo de step:

```json
{
  "sequence": 1,
  "name": "Criar pedido",
  "action": {
    "type": "http",
    "method": "POST",
    "url": "https://orders.example.com/orders",
    "body": {"product_id": 42},
    "timeout_seconds": 30
  },
  "assertions": [
    {"target": "status_code", "operator": "equals", "expected": 201},
    {"target": "body", "path": "status", "expected": "created"}
  ]
}
```

`sequence` é opcional na criação. Quando omitida, a API usa a próxima posição
do plano. A reordenação recebe todos os steps com sequências contíguas:

```json
{"steps": [{"step_id": 2, "sequence": 1}, {"step_id": 1, "sequence": 2}]}
```

Execução imediata:

```bash
curl -X POST http://localhost:8000/plans/1/executions \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Execução futura usa uma data ISO 8601 com timezone:

```json
{"scheduled_for": "2026-06-28T18:00:00-03:00"}
```

### Variáveis entre steps

Um step pode extrair valores da resposta e os próximos steps podem usar
templates `{{variavel}}` na URL, headers, body e valores esperados dos asserts.
As variáveis pertencem à execução do plano e são persistidas no PostgreSQL.

Exemplo de login que captura um token:

```json
{
  "name": "Login",
  "action": {
    "method": "POST",
    "url": "https://api.example.com/auth",
    "body": {"email": "qa@example.com", "password": "secret"}
  },
  "assertions": [{"target": "status_code", "expected": 200}],
  "extracts": {"access_token": "body.access_token"}
}
```

O step seguinte reutiliza o valor:

```json
{
  "name": "Consultar perfil",
  "action": {
    "method": "GET",
    "url": "https://api.example.com/me",
    "headers": {"Authorization": "Bearer {{access_token}}"}
  },
  "assertions": [
    {"target": "status_code", "expected": 200},
    {"target": "body", "path": "email", "expected": "qa@example.com"}
  ]
}
```

As fontes suportadas para extração são `body.caminho.aninhado`,
`header.Nome-Do-Header` e `status_code`. Também é possível fornecer variáveis
iniciais ao iniciar uma execução:

```json
{"variables": {"tenant": "acme"}}
```

## Realtime e controle

Conecte ao WebSocket para acompanhar o plano inteiro. Os eventos informam
`plan_id`, `execution_id`, step atual, quantidade concluída e total de steps.
O próximo step só é enfileirado após `step.execution.completed.v1`; uma falha
encerra a execução do plano.
Para controlar uma execução, envie:

```json
{"command": "stop", "execution_id": "uuid"}
```

ou:

```json
{"command": "restart", "execution_id": "uuid"}
```

O comando também vira evento no Kafka. O dispatcher revoga ou recria a task Celery.

## Banco e migrações

```bash
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1
.venv/bin/alembic revision --autogenerate -m "descricao"
```

## Qualidade

```bash
.venv/bin/pyright
.venv/bin/pytest
RUN_INTEGRATION_TESTS=1 .venv/bin/pytest tests/integration -v --no-cov
```

Os testes de integração usam Testcontainers e exigem Docker.
