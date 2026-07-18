# Sentinel AI

Sentinel AI is an Engineering Operations Agent for GitHub. It accepts an investigation request, plans the smallest relevant set of specialist agents, gathers provider evidence in parallel, correlates that evidence, and returns a GitHub-ready Markdown report.

> Current state: repository reads and webhook-triggered investigations are implemented. Sentinel does **not yet publish its result back as a GitHub comment**; the webhook response contains the generated Markdown. Use the REST endpoint or webhook response while a GitHub App comment-delivery worker is added.

## What is included

- FastAPI REST API and GitHub webhook endpoint
- GitHub REST, GitHub Actions, Prometheus, Loki, Grafana, Argo CD, Kubernetes, and ChromaDB connectors
- Async agent execution, dynamic planning, evidence graph, root-cause ranking, recommendations, and SSE progress streaming
- SQLAlchemy models and Alembic configuration
- Python 3.12 development environment and test suite

## Requirements

Install these before starting:

- Python **3.12** (`python3.12 --version`)
- Git
- A reachable PostgreSQL 15+ instance if incident persistence is enabled
- Redis 7+ for the upcoming distributed/cache features
- ChromaDB for historical incident search
- Access to whichever observability providers you want Sentinel to query

The application can start without external providers. Missing provider configuration is reported as unavailable evidence; Sentinel does not fabricate telemetry.

## 1. Create the Python environment

From the repository root:

```bash
cd backend
/usr/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

Activate it if preferred:

```bash
source .venv/bin/activate
```

## 2. Create environment configuration

Copy the checked-in template, then edit the new file. Do not commit `.env`.

```bash
cd backend
cp .env.example .env
```

### Core configuration

```env
SENTINEL_ENVIRONMENT=development
SENTINEL_DATABASE_URL=postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel
SENTINEL_REDIS_URL=redis://localhost:6379/0
SENTINEL_AGENT_TIMEOUT_SECONDS=20
SENTINEL_CONNECTOR_CACHE_TTL_SECONDS=60
SENTINEL_JWT_SECRET=replace-with-a-long-random-secret
```

`SENTINEL_AGENT_TIMEOUT_SECONDS` is the maximum duration for one specialist agent. An expired agent is returned as unavailable evidence while the rest of the investigation continues.

### Optional OpenAI planner configuration

Without an OpenAI key, Sentinel uses a conservative local intent classifier. With a key, the planner uses a constrained structured-JSON decision and can select only registered agents.

```env
SENTINEL_OPENAI_API_KEY=your-api-key
SENTINEL_OPENAI_MODEL=gpt-4.1-mini
```

### Provider configuration

Only configure providers that exist in your environment.

```env
# GitHub REST and GitHub Actions
SENTINEL_GITHUB_TOKEN=github_pat_your_token
SENTINEL_GITHUB_API_URL=https://api.github.com

# Metrics and logs
SENTINEL_PROMETHEUS_URL=https://prometheus.internal.example
SENTINEL_LOKI_URL=https://loki.internal.example

# Optional dashboard discovery
SENTINEL_GRAFANA_URL=https://grafana.internal.example
SENTINEL_GRAFANA_TOKEN=your-grafana-service-account-token

# Deployment state
SENTINEL_ARGOCD_URL=https://argocd.internal.example
SENTINEL_ARGOCD_TOKEN=your-argocd-token

# Historical incident similarity
SENTINEL_CHROMA_HOST=localhost
SENTINEL_CHROMA_PORT=8000
```

For Kubernetes, Sentinel uses the official async Kubernetes client. It loads in-cluster credentials when running in Kubernetes; otherwise it uses your active kubeconfig context. Ensure the identity has least-privilege read access to Pods, Events, Deployments, ReplicaSets, and pod logs in the target namespaces.

## 3. Start supporting services

For a local development environment, start PostgreSQL, Redis, and ChromaDB using your organization’s approved deployment method. Their connection details must match `.env`.

At minimum, ChromaDB must be reachable before historical-incidence queries can work. PostgreSQL is required when the SQLAlchemy repository is wired into the production composition root. Redis is configured now for the caching/worker boundary and can be introduced when those services are enabled.

## 4. Start Sentinel

```bash
cd backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Confirm it is running:

```bash
curl http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

Interactive API documentation is available at `http://localhost:8000/docs`.

## 5. Connect an existing GitHub repository

### Create a GitHub token

The current connector authenticates with a GitHub fine-grained Personal Access Token (PAT). Create one restricted to the repository Sentinel will investigate, then assign read-only permissions for:

- Metadata
- Contents (commits, branches, releases, commit details)
- Pull requests
- Issues
- Actions (workflow runs, jobs, and logs)

Set it in `.env`:

```env
SENTINEL_GITHUB_TOKEN=github_pat_...
```

Use a dedicated machine-user token in shared environments, rotate it through your secret manager, and never put it in source control. Fine-grained tokens can be limited to individual repositories: <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens>.

### Make the API reachable by GitHub

GitHub webhooks need a public HTTPS endpoint. In production, place Sentinel behind your organization’s HTTPS ingress or reverse proxy:

```text
https://sentinel.example.com/v1/github/webhooks
```

For local development, expose port 8000 with an HTTPS tunnel such as ngrok or Cloudflare Tunnel. Use the public tunnel URL followed by `/v1/github/webhooks`.

### Create the repository webhook

In the target GitHub repository:

1. Open **Settings → Webhooks → Add webhook**.
2. Set **Payload URL** to `https://your-public-host/v1/github/webhooks`.
3. Set **Content type** to `application/json`.
4. Generate a long random **Secret**.
5. Subscribe to **Issue comments**. GitHub uses this event for comments on both issues and pull requests.
6. Save the webhook and use GitHub’s delivery view to confirm a successful `2xx` response.

Set the same secret in Sentinel:

```env
SENTINEL_GITHUB_WEBHOOK_SECRET=the-exact-webhook-secret
```

Sentinel rejects any webhook whose `X-Hub-Signature-256` does not validate. GitHub’s webhook setup guide: <https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks>.

### Invoke Sentinel from GitHub

Create a comment on an issue or pull request such as:

```text
@sentinel investigate checkout-service failing
```

The current webhook accepts `@sentinel` and `/sentinel` prefixes. The planner recognizes investigations involving latency, deployments, pipelines, Kubernetes, cloud/cost impact, and historical incidents.

## 6. Use the REST API directly

Use this when testing connectors or before GitHub comment publishing is enabled:

```bash
curl -X POST http://localhost:8000/v1/investigations \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_id": "acme",
    "repository": "acme/checkout-service",
    "service": "checkout-service",
    "query": "Why is checkout-service failing?",
    "time_range_minutes": 60
  }'
```

The response contains `summary`, structured `evidence`, ranked `root_causes`, recommendations, impact fields, historical incidents, and `github_markdown`.

## 7. Stream investigation progress

Use the SSE endpoint to receive planning and agent progress before the final response:

```bash
curl -N -X POST http://localhost:8000/v1/investigations/stream \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_id": "acme",
    "repository": "acme/checkout-service",
    "service": "checkout-service",
    "query": "Investigate checkout latency"
  }'
```

Events are emitted as `progress` during planning, connector execution, and evidence correlation, followed by one `complete` event carrying the serialized investigation response.

## 8. Verify the installation

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check app
```

## Architecture

```text
GitHub webhook / REST API
        ↓
Planner (structured LLM plan or safe fallback)
        ↓
Parallel stateless specialist agents
        ↓
Evidence bundle + correlation graph
        ↓
Root-cause ranking → recommendations → GitHub-ready Markdown
```

Each provider adapter implements `BaseConnector`; each specialist implements `BaseAgent`. This keeps provider-specific auth and payload formats separate from planning and investigation logic.

## Security checklist

- Keep `.env`, PATs, provider tokens, and webhook secrets out of Git.
- Use repository-scoped, read-only GitHub permissions wherever possible.
- Restrict the webhook endpoint at the network layer and always set `SENTINEL_GITHUB_WEBHOOK_SECRET`.
- Use TLS for all provider endpoints.
- Grant Kubernetes read-only RBAC to only the required namespaces.
- Rotate credentials through a secret manager; do not rely on developer workstations for production tokens.
- Do not expose `/docs` publicly in production without access controls.

## Current implementation boundaries

- GitHub comment publication requires a write-enabled GitHub App/PAT adapter and is not implemented yet.
- OAuth/JWT enforcement, Redis cache use, Celery distributed workers, OpenTelemetry exporters, Docker Compose, and production database migrations are planned extensions.
- The included Alembic setup has no generated initial revision yet; generate and review one before enabling persistent production data.
