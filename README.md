# PulseMetrics — Customer Purchases API & Dashboard

A production-grade microservices app demonstrating Kubernetes orchestration, CI/CD, database migrations, observability, and REST API design.

**Stack:** FastAPI · React · Streamlit · PostgreSQL · Alembic · Redis · Docker · Kubernetes · Helm · Prometheus · GitHub Actions

Two frontends are shipped intentionally in parallel, not as a migration: **React** (TypeScript, TanStack Query, Recharts) is the primary component-based dashboard, and **Streamlit** remains as a rapid-prototyping/analyst view — demonstrating both approaches against the same API.

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                          Kubernetes Cluster                           │
│                                                                       │
│  ┌───────────┐      ┌──────────────┐      ┌────────────────────┐     │
│  │  React    │─────▶│   FastAPI    │─────▶│     PostgreSQL     │     │
│  │  (SPA)    │      │  (REST API)  │      │  (Alembic schema)  │     │
│  └───────────┘      │              │      └────────────────────┘     │
│  ┌───────────┐      │  JWT auth    │                                 │
│  │ Streamlit │─────▶│  Prometheus  │      ┌────────────────────┐     │
│  │ (Plotly   │      │  Rate limit  │─────▶│       Redis        │     │
│  │ dashboard)│      │  JSON logs   │      │   (KPI cache)      │     │
│  └───────────┘      │              │      └────────────────────┘     │
│        │             │              │      ┌────────────────────┐     │
│        │             │              │─────▶│  Init container    │     │
│        └── Ingress (nginx, host-routed)    │  alembic upgrade   │     │
│                                            └────────────────────┘     │
└───────────────────────────────────────────────────────────────────────┘
                              │
                    GitHub Actions CI/CD
              (lint · test · kubeconform · Trivy)
```

---

## Features

| Feature | Details |
|---|---|
| REST API | Add single/bulk purchases, paginated list, filter by country & date, KPIs, sales forecast, soft delete |
| JWT Auth | Registration, login, and role-based access (`admin`/`user`); write endpoints require a Bearer token |
| Soft Deletes | `DELETE /purchase/{id}` sets `deleted_at`; all read queries filter deleted rows, never hard-deletes |
| Redis Caching | KPI endpoint cached in Redis with 60s TTL; invalidated automatically on any write |
| PostgreSQL | Persistent storage with SQLAlchemy ORM, connection pooling, audit columns (`created_at`, `updated_at`) |
| Alembic | Versioned migrations (`0001`→`0004`) — applied by init container on every deploy |
| Kubernetes | Deployments, Services, ConfigMap, Secret, PVC, Ingress, HPA |
| Auto-scaling | HorizontalPodAutoscaler scales FastAPI 2→10 pods on CPU/memory pressure |
| Health probes | `/healthz` (liveness) and `/readyz` (readiness, checks DB) wired into K8s |
| Prometheus | `/metrics` endpoint with pod-level scraping annotations |
| Structured logging | JSON-formatted logs with timestamp, level, and module |
| Rate limiting | 100 req/min on `GET /purchases/`, 30 req/min on KPIs |
| Plotly charts | Interactive bar, area, and line charts with hover tooltips (Streamlit) |
| React dashboard | TypeScript SPA (Vite, TanStack Query, React Hook Form + Zod, Recharts, Tailwind); full feature parity with the Streamlit dashboard, including admin-gated delete and CSV export |
| Runtime-configurable frontend | React reads `API_URL` from a container-injected `env-config.js` at startup (not baked in at build time), so one built image promotes across dev/UAT/prod — same pattern Streamlit already uses via `os.getenv` |
| Helm chart | Single command deploys the full stack; separate values for dev/UAT/prod |
| CI/CD | GitHub Actions — lint (ruff + oxlint + tsc), test (pytest + Vitest, with coverage), kubeconform, Trivy scan on PR; push to ghcr.io on merge |
| Dependabot | Weekly dependency updates for pip, npm, Docker base images, and GitHub Actions |
| Pre-commit hooks | ruff lint + format enforced locally before every commit |

---

## Quick Start

### Option A — Makefile (recommended)

The Makefile automates every step. Run `make doctor` first to verify prerequisites.

```bash
# Check tools are installed
make doctor

# Install missing tools (kubectl, minikube, helm) and pre-commit hooks
make setup

# Start Minikube cluster
make start

# Build Docker images into Minikube's registry
make build

# Deploy to dev environment
make dev

# Add /etc/hosts entries for local DNS
make hosts
```

Access the React dashboard at http://dev.react.purchases.local and the Streamlit dashboard at http://dev.purchases.local after running `make hosts`.

Other environment targets:
```bash
make uat    # deploy to purchases-uat namespace
make prod   # deploy to purchases-prod namespace
```

Monitor and clean up:
```bash
make status ENV=dev     # pods, HPA, ingress
make logs ENV=dev       # tail FastAPI logs
make clean ENV=dev      # uninstall + delete namespace
make clean-all          # remove all envs and stop Minikube
```

---

### Option B — Docker Compose (local dev, no Kubernetes)

```bash
docker compose up --build
```

The `migrate` service runs `alembic upgrade head` automatically before the API starts.

| Service | URL |
|---|---|
| React dashboard | http://localhost:3000 |
| Streamlit dashboard | http://localhost:8501 |
| FastAPI docs | http://localhost:8000/docs |
| Prometheus metrics | http://localhost:8000/metrics |

### React dashboard — local dev without Docker

```bash
cd react
npm install
npm run dev
```

Runs on http://localhost:5173, resolving `API_URL` via (in order): a container-injected `window.__ENV__` (production only), `VITE_API_URL` from a local `.env` (copy `.env.example`), or falling back to `http://localhost:8000`. Run tests with `npm run test`.

---

### Option C — Kubernetes manual steps

```bash
# 1. Start Minikube
minikube start
minikube addons enable ingress
minikube addons enable metrics-server

# 2. Build images into Minikube
eval $(minikube docker-env)
docker build ./fastapi -t ghcr.io/<your-github-username>/purchases-fastapi:latest
docker build ./streamlit -t ghcr.io/<your-github-username>/purchases-streamlit:latest
docker build ./react -t ghcr.io/<your-github-username>/purchases-react:latest

# 3. Deploy with Helm
helm upgrade --install purchases-dev ./helm \
  -f helm/values.yaml -f helm/values-dev.yaml \
  --set fastapi.image=ghcr.io/<your-github-username>/purchases-fastapi \
  --set streamlit.image=ghcr.io/<your-github-username>/purchases-streamlit \
  --set react.image=ghcr.io/<your-github-username>/purchases-react \
  --set fastapi.imagePullPolicy=Never \
  --set streamlit.imagePullPolicy=Never \
  --set react.imagePullPolicy=Never \
  --create-namespace

# 4. Add DNS entries
echo "$(minikube ip) purchases.local api.purchases.local react.purchases.local" | sudo tee -a /etc/hosts
```

---

## Database Migrations (Alembic)

Schema changes are managed through versioned migrations in `fastapi/alembic/versions/`.

```bash
# Apply all pending migrations
cd fastapi && alembic upgrade head

# Check for model/migration drift (run in CI)
alembic check

# Generate a migration after changing models.py
alembic revision --autogenerate -m "add deleted_at column"

# Roll back one migration
alembic downgrade -1

# View migration history
alembic history --verbose
```

In Kubernetes, an **init container** runs `alembic upgrade head` before the FastAPI pod starts on every deploy, so schema and code are always in sync.

---

## Running Tests

```bash
cd fastapi
pip install -r requirements.txt
pytest test_main.py -v --cov=. --cov-report=term-missing
```

Tests use an in-memory SQLite database — no PostgreSQL required.

React's own test suite (Vitest + React Testing Library) covers the auth interceptor (silent token refresh, concurrent-401 deduplication), forms, and page-level data flows:

```bash
cd react
npm install
npm run test
```

---

## Auth token storage — a known trade-off

Both frontends store JWTs client-side (Streamlit in `st.session_state`, React in `localStorage`) rather than an httpOnly cookie, because the backend is Bearer-token-only by design (no cookie-based session). This is a deliberate, documented choice, not an oversight: no XSS-hardening claim is made, and it matches the trust model the API already commits to. Delete/admin actions are still enforced server-side regardless of what the client believes about its own role — client-side gating is UX only.

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/register` | — | Create a new user account |
| `POST` | `/token` | — | Login — returns a JWT Bearer token |
| `GET` | `/users/me` | Required | Returns the current authenticated user |
| `POST` | `/purchase/` | Required | Add a single purchase |
| `POST` | `/purchase/bulk/` | Required | Upload purchases from CSV |
| `DELETE` | `/purchase/{id}` | Required | Soft-delete a purchase by ID |
| `GET` | `/purchases/` | — | List purchases — filter by `country`, `start_date`, `end_date`; paginate with `limit` & `offset` |
| `GET` | `/purchases/kpis` | — | KPIs + optional sales forecast (`?forecast_days=N`); cached in Redis for 60s |
| `GET` | `/healthz` | — | Liveness probe |
| `GET` | `/readyz` | — | Readiness probe (checks DB connection) |
| `GET` | `/metrics` | — | Prometheus metrics |

---

## CI/CD Pipeline

| Trigger | Jobs |
|---|---|
| Every push / PR to `main` | Lint (ruff on fastapi/streamlit, oxlint + tsc + Vitest on react), pytest + coverage, `alembic check`, Helm lint, kubeconform schema validation, Docker build + Trivy vulnerability scan (all three images) |
| Merge to `main` | Build + push images to `ghcr.io` with `latest` and commit-SHA tags |
| Git tag `v*` | Push UAT-tagged images |
| `workflow_dispatch` | Manual prod deploy |

Images are published to:
```
ghcr.io/<your-github-username>/purchases-fastapi
ghcr.io/<your-github-username>/purchases-streamlit
ghcr.io/<your-github-username>/purchases-react
```

---

## Observability — Prometheus & Grafana

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# Forward Grafana to localhost
kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring
```

Grafana: http://localhost:3000 (user: `admin`, pass: `prom-operator`).

FastAPI pods have Prometheus scraping annotations — metrics appear automatically.

---

## Project Structure

```
.
├── fastapi/
│   ├── main.py               # API endpoints, JWT auth, rate limiting, Redis cache, structured logging
│   ├── auth.py               # JWT token creation/validation, password hashing, user dependency
│   ├── database.py           # SQLAlchemy engine, session dependency, naming conventions
│   ├── models.py             # ORM models: PurchaseRecord (soft delete, audit cols), UserRecord
│   ├── alembic.ini           # Alembic config (DB URL read from environment)
│   ├── alembic/
│   │   ├── env.py            # Migration runner — imports Base.metadata for autogenerate
│   │   ├── script.py.mako    # Template for generated migration files
│   │   └── versions/
│   │       ├── 0001_create_purchases_table.py
│   │       ├── 0002_add_audit_columns.py
│   │       ├── 0003_add_users_table.py
│   │       └── 0004_add_soft_delete.py
│   ├── test_main.py          # pytest suite — 20 tests, 91% coverage (SQLite, no Postgres needed)
│   ├── requirements.txt
│   └── Dockerfile
├── streamlit/
│   ├── app.py                # Auth UI, Plotly charts, delete UI, pagination, currency conversion
│   ├── .streamlit/
│   │   └── config.toml       # Custom theme
│   ├── requirements.txt
│   └── Dockerfile
├── react/
│   ├── src/
│   │   ├── api/               # axios client (Bearer + silent-refresh interceptor), typed endpoints
│   │   ├── auth/               # AuthContext/Provider, useAuth, ProtectedRoute
│   │   ├── components/
│   │   │   ├── ui/             # hand-rolled Button/Input/Select/Card/ConfirmDialog (no UI kit)
│   │   │   ├── layout/         # AppShell nav
│   │   │   ├── purchases/      # table, filters, pagination, forms, bulk upload, delete
│   │   │   └── dashboard/      # KPI tiles + Recharts charts (revenue, top customers, forecast)
│   │   ├── hooks/               # TanStack Query hooks (usePurchases, useKpis, mutations)
│   │   ├── lib/                  # currency conversion (ported from streamlit/app.py), CSV parse/export
│   │   ├── pages/                # route-level pages
│   │   └── config.ts             # resolves API_URL: window.__ENV__ -> VITE_API_URL -> default
│   ├── public/env-config.js       # dev-mode placeholder, overwritten in the container at startup
│   ├── docker-entrypoint.sh       # injects the real API_URL into env-config.js at container start
│   ├── nginx.conf                 # SPA fallback (try_files) + no-cache on env-config.js
│   ├── Dockerfile                 # multi-stage: node build -> nginx-unprivileged serve
│   └── package.json
├── k8s/                      # Raw Kubernetes manifests
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── namespace.yaml
│   ├── postgres-deployment.yaml
│   ├── postgres-service.yaml
│   ├── postgres-pvc.yaml
│   ├── redis-deployment.yaml
│   ├── redis-service.yaml
│   ├── fastapi-deployment.yaml
│   ├── fastapi-service.yaml
│   ├── fastapi-hpa.yaml
│   ├── streamlit-deployment.yaml
│   ├── streamlit-service.yaml
│   ├── react-deployment.yaml
│   ├── react-service.yaml
│   └── ingress.yaml          # host-based routing: purchases.local / api.purchases.local / react.purchases.local
├── helm/                     # Helm chart with dev/uat/prod values files
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-uat.yaml
│   ├── values-prod.yaml
│   └── templates/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml            # PR: lint (ruff + oxlint/tsc/vitest), test, kubeconform, Trivy
│   │   └── cd.yml            # main: push images to ghcr.io
│   └── dependabot.yml        # Weekly updates for pip, npm, Docker, Actions
├── .pre-commit-config.yaml   # ruff lint + format on commit
├── pyproject.toml            # ruff config
├── Makefile                  # doctor, setup, start, build, dev/uat/prod, clean
└── docker-compose.yml        # Local dev: postgres + redis + migrate + fastapi + streamlit + react
```
