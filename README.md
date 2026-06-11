# Customer Purchases API & Dashboard

A production-grade microservices app demonstrating Kubernetes orchestration, observability, CI/CD, and REST API design.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                   │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  Streamlit   │───▶│   FastAPI    │───▶│ PostgreSQL│  │
│  │  (dashboard) │    │  (REST API)  │    │    (DB)   │  │
│  └──────────────┘    └──────────────┘    └───────────┘  │
│          │                  │                            │
│          └────── Ingress ───┘                            │
│                  (nginx)                                 │
└─────────────────────────────────────────────────────────┘
```

**Stack:** FastAPI · Streamlit · PostgreSQL · Docker · Kubernetes · Helm · Prometheus · GitHub Actions

---

## Features

| Feature | Details |
|---|---|
| REST API | Add single/bulk purchases, filter by country & date, KPIs, sales forecast |
| PostgreSQL | Persistent storage with SQLAlchemy ORM and connection pooling |
| Kubernetes | Deployments, Services, ConfigMap, Secret, PVC, Ingress, HPA |
| Auto-scaling | HorizontalPodAutoscaler scales FastAPI 2→10 pods on CPU/memory pressure |
| Health probes | `/healthz` (liveness) and `/readyz` (readiness, checks DB) wired into K8s |
| Prometheus | `/metrics` endpoint with pod-level scraping annotations |
| Structured logging | JSON-formatted logs with timestamp, level, and module |
| Rate limiting | 100 req/min on GET /purchases, 30 req/min on KPIs |
| Helm chart | Single `helm install` deploys the entire stack |
| CI/CD | GitHub Actions — lint, test, Docker build on PR; push to ghcr.io on merge |

---

## Quick Start

### Docker Compose (local dev)

```bash
docker-compose up --build
```

- Streamlit: http://localhost:8501
- FastAPI docs: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics

---

### Kubernetes with Minikube (free, local)

#### 1. Install prerequisites
```bash
# Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

#### 2. Start Minikube and enable addons
```bash
minikube start
minikube addons enable ingress
minikube addons enable metrics-server   # required for HPA
```

#### 3a. Deploy with kubectl
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
```

#### 3b. Deploy with Helm (recommended)
```bash
helm install purchases ./helm
```

To override values (e.g. different image tag):
```bash
helm install purchases ./helm --set fastapi.tag=abc123
```

#### 4. Configure local DNS
```bash
echo "$(minikube ip) purchases.local api.purchases.local" | sudo tee -a /etc/hosts
```

#### 5. Access the app
- Dashboard: http://purchases.local
- API docs: http://api.purchases.local/docs
- Metrics: http://api.purchases.local/metrics

#### 6. Watch auto-scaling in action
```bash
# Watch pods
kubectl get pods -n purchases -w

# Watch HPA
kubectl get hpa -n purchases -w
```

---

### Observability — Prometheus & Grafana

Install the kube-prometheus-stack (all free, runs in Minikube):

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# Forward Grafana to localhost
kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring
```

Grafana is at http://localhost:3000 (user: `admin`, pass: `prom-operator`).

The FastAPI pods have Prometheus scraping annotations, so metrics appear automatically.

---

## Running Tests

```bash
cd fastapi
pip install -r requirements.txt
pytest test_main.py -v
```

Tests use an in-memory SQLite database — no PostgreSQL needed.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/purchase/` | Add a single purchase |
| POST | `/purchase/bulk/` | Upload purchases from CSV |
| GET | `/purchases/` | List purchases (filter by country, date) |
| GET | `/purchases/kpis` | KPIs + optional sales forecast |
| GET | `/healthz` | Liveness probe |
| GET | `/readyz` | Readiness probe (checks DB) |
| GET | `/metrics` | Prometheus metrics |

---

## CI/CD Pipeline

| Trigger | Jobs |
|---|---|
| Pull request to `main` | Lint (ruff), pytest, Docker build validation |
| Push to `main` | Build + push images to `ghcr.io` with `latest` and commit-SHA tags |

Images are published to:
- `ghcr.io/apayne185/purchases-fastapi`
- `ghcr.io/apayne185/purchases-streamlit`

---

## Project Structure

```
.
├── fastapi/
│   ├── main.py          # API endpoints, rate limiting, structured logging
│   ├── database.py      # SQLAlchemy engine + session dependency
│   ├── models.py        # ORM model (PurchaseRecord)
│   ├── test_main.py     # pytest suite (SQLite in-memory)
│   ├── requirements.txt
│   └── Dockerfile
├── streamlit/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── k8s/                 # Raw Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── postgres-pvc.yaml
│   ├── postgres-deployment.yaml
│   ├── postgres-service.yaml
│   ├── fastapi-deployment.yaml
│   ├── fastapi-service.yaml
│   ├── fastapi-hpa.yaml
│   ├── streamlit-deployment.yaml
│   ├── streamlit-service.yaml
│   └── ingress.yaml
├── helm/                # Helm chart (parameterised K8s manifests)
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── .github/
│   └── workflows/
│       ├── ci.yml       # PR: lint + test + build
│       └── cd.yml       # main: push images to ghcr.io
└── docker-compose.yml
```
