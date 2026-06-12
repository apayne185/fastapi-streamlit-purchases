# Customer Purchases API & Dashboard

A production-grade microservices app demonstrating Kubernetes orchestration, CI/CD, database migrations, observability, and REST API design.

**Stack:** FastAPI · Streamlit · PostgreSQL · Alembic · Docker · Kubernetes · Helm · Prometheus · GitHub Actions

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                        │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │  Streamlit   │───▶│   FastAPI    │───▶│     PostgreSQL     │  │
│  │  (Plotly     │    │  (REST API)  │    │  (Alembic schema)  │  │
│  │  dashboard)  │    │              │    └────────────────────┘  │
│  └──────────────┘    │  Prometheus  │                            │
│          │           │  Rate limit  │    ┌────────────────────┐  │
│          │           │  JSON logs   │───▶│  Init container    │  │
│          └──── Ingress (nginx) ─────┘    │  alembic upgrade   │  │
│                                          └────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
                    GitHub Actions CI/CD
              (lint · test · kubeconform · Trivy)
```

---

## Features

| Feature | Details |
|---|---|
| REST API | Add single/bulk purchases, paginated list, filter by country & date, KPIs, sales forecast |
| PostgreSQL | Persistent storage with SQLAlchemy ORM, connection pooling, audit columns |
| Alembic | Versioned database migrations — `alembic upgrade head` applied by init container on every deploy |
| Kubernetes | Deployments, Services, ConfigMap, Secret, PVC, Ingress, HPA |
| Auto-scaling | HorizontalPodAutoscaler scales FastAPI 2→10 pods on CPU/memory pressure |
| Health probes | `/healthz` (liveness) and `/readyz` (readiness, checks DB) wired into K8s |
| Prometheus | `/metrics` endpoint with pod-level scraping annotations |
| Structured logging | JSON-formatted logs with timestamp, level, and module |
| Rate limiting | 100 req/min on `GET /purchases/`, 30 req/min on KPIs |
| Plotly charts | Interactive bar, area, and line charts with hover tooltips |
| Helm chart | Single command deploys the full stack; separate values for dev/UAT/prod |
| CI/CD | GitHub Actions — lint, test (with coverage), kubeconform, Trivy scan on PR; push to ghcr.io on merge |
| Dependabot | Weekly dependency updates for pip, Docker base images, and GitHub Actions |
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

Access the app at http://dev.purchases.local after running `make hosts`.

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
| Streamlit dashboard | http://localhost:8501 |
| FastAPI docs | http://localhost:8000/docs |
| Prometheus metrics | http://localhost:8000/metrics |

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

# 3. Deploy with Helm
helm upgrade --install purchases-dev ./helm \
  -f helm/values.yaml -f helm/values-dev.yaml \
  --set fastapi.image=ghcr.io/<your-github-username>/purchases-fastapi \
  --set streamlit.image=ghcr.io/<your-github-username>/purchases-streamlit \
  --set fastapi.imagePullPolicy=Never \
  --set streamlit.imagePullPolicy=Never \
  --create-namespace

# 4. Add DNS entries
echo "$(minikube ip) purchases.local api.purchases.local" | sudo tee -a /etc/hosts
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

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/purchase/` | Add a single purchase |
| `POST` | `/purchase/bulk/` | Upload purchases from CSV |
| `GET` | `/purchases/` | List purchases — filter by `country`, `start_date`, `end_date`; paginate with `limit` & `offset` |
| `GET` | `/purchases/kpis` | KPIs + optional sales forecast (`?forecast_days=N`) |
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/readyz` | Readiness probe (checks DB connection) |
| `GET` | `/metrics` | Prometheus metrics |

---

## CI/CD Pipeline

| Trigger | Jobs |
|---|---|
| Every push / PR to `main` | Lint (ruff), pytest + coverage, `alembic check`, Helm lint, kubeconform schema validation, Docker build + Trivy vulnerability scan |
| Merge to `main` | Build + push images to `ghcr.io` with `latest` and commit-SHA tags |
| Git tag `v*` | Push UAT-tagged images |
| `workflow_dispatch` | Manual prod deploy |

Images are published to:
```
ghcr.io/<your-github-username>/purchases-fastapi
ghcr.io/<your-github-username>/purchases-streamlit
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
│   ├── main.py               # API endpoints, rate limiting, structured logging
│   ├── database.py           # SQLAlchemy engine, session dependency, naming conventions
│   ├── models.py             # ORM model (PurchaseRecord) with audit columns
│   ├── alembic.ini           # Alembic config (DB URL read from environment)
│   ├── alembic/
│   │   ├── env.py            # Migration runner — imports Base.metadata for autogenerate
│   │   ├── script.py.mako    # Template for generated migration files
│   │   └── versions/
│   │       └── 0001_create_purchases_table.py
│   ├── test_main.py          # pytest suite (SQLite in-memory, no Postgres needed)
│   ├── requirements.txt
│   └── Dockerfile
├── streamlit/
│   ├── app.py                # Plotly charts, form validation, currency conversion
│   ├── .streamlit/
│   │   └── config.toml       # Custom theme
│   ├── requirements.txt
│   └── Dockerfile
├── k8s/                      # Raw Kubernetes manifests
├── helm/                     # Helm chart with dev/uat/prod values files
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-uat.yaml
│   ├── values-prod.yaml
│   └── templates/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml            # PR: lint, test, kubeconform, Trivy
│   │   └── cd.yml            # main: push images to ghcr.io
│   └── dependabot.yml        # Weekly updates for pip, Docker, Actions
├── .pre-commit-config.yaml   # ruff lint + format on commit
├── pyproject.toml            # ruff config
├── Makefile                  # doctor, setup, start, build, dev/uat/prod, clean
└── docker-compose.yml        # Local dev: postgres + migrate + fastapi + streamlit
```
