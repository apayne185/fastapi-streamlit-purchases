ENV   ?= dev
# Set LOCAL=false when deploying to a real cluster that can pull from ghcr.io
LOCAL ?= true

# Auto-detect GitHub username from the git remote (works for any fork/clone)
GITHUB_USER ?= $(shell git remote get-url origin 2>/dev/null | sed -E 's|.*github\.com[:/]([^/]+)/.*|\1|')
IMAGE_FASTAPI   := ghcr.io/$(GITHUB_USER)/purchases-fastapi
IMAGE_STREAMLIT := ghcr.io/$(GITHUB_USER)/purchases-streamlit

# When LOCAL=true, override imagePullPolicy to Never so Minikube uses local images
ifeq ($(LOCAL),true)
PULL_POLICY_FLAGS := --set fastapi.imagePullPolicy=Never --set streamlit.imagePullPolicy=Never
else
PULL_POLICY_FLAGS :=
endif

.PHONY: setup start build deploy dev uat prod hosts status logs clean all

## ── One-shot full startup ─────────────────────────────────────────────────────
all: start build deploy hosts
	@echo ""
	@echo "Stack is up. Access:"
	@echo "  Dashboard : http://$(shell grep -m1 'purchases.local' /etc/hosts | awk '{print $$2}' || echo 'purchases.local')"
	@echo "  API docs  : http://api.purchases.local/docs"
	@echo "  Metrics   : http://api.purchases.local/metrics"

## ── Tool installation (run once) ─────────────────────────────────────────────
setup:
	@echo "→ Installing kubectl..."
	curl -LO "https://dl.k8s.io/release/$$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
	sudo install kubectl /usr/local/bin/kubectl && rm kubectl
	@echo "→ Installing minikube..."
	curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
	sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
	@echo "→ Installing helm..."
	curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

## ── Cluster ───────────────────────────────────────────────────────────────────
start:
	minikube start
	minikube addons enable ingress
	minikube addons enable metrics-server
	@echo "→ Cluster ready"

## ── Docker images ─────────────────────────────────────────────────────────────
build:
	eval $$(minikube docker-env) && \
	docker build ./fastapi -t $(IMAGE_FASTAPI):latest && \
	docker build ./streamlit -t $(IMAGE_STREAMLIT):latest
	@echo "→ Images built into Minikube"

## ── Helm deploy (default ENV=dev) ────────────────────────────────────────────
deploy:
	helm upgrade --install purchases-$(ENV) ./helm \
		-f helm/values.yaml \
		-f helm/values-$(ENV).yaml \
		--set fastapi.image=$(IMAGE_FASTAPI) \
		--set streamlit.image=$(IMAGE_STREAMLIT) \
		$(PULL_POLICY_FLAGS) \
		--create-namespace
	@echo "→ Deployed to ENV=$(ENV) — run 'make status ENV=$(ENV)' to monitor pods"

dev:
	$(MAKE) deploy ENV=dev

uat:
	$(MAKE) deploy ENV=uat

prod:
	$(MAKE) deploy ENV=prod

## ── /etc/hosts ────────────────────────────────────────────────────────────────
hosts:
	@MINIKUBE_IP=$$(minikube ip) && \
	echo "$$MINIKUBE_IP purchases.local api.purchases.local \
	dev.purchases.local dev.api.purchases.local \
	uat.purchases.local uat.api.purchases.local" | sudo tee -a /etc/hosts
	@echo "→ /etc/hosts updated"

## ── Observability ─────────────────────────────────────────────────────────────
status:
	@echo "=== Pods ==="
	kubectl get pods -n purchases-$(ENV)
	@echo "\n=== HPA ==="
	kubectl get hpa -n purchases-$(ENV)
	@echo "\n=== Ingress ==="
	kubectl get ingress -n purchases-$(ENV)

logs:
	kubectl logs -n purchases-$(ENV) -l app=fastapi --tail=50 -f

## ── Teardown ──────────────────────────────────────────────────────────────────
clean:
	helm uninstall purchases-$(ENV) --namespace purchases-$(ENV) || true
	kubectl delete namespace purchases-$(ENV) || true
	@echo "→ ENV=$(ENV) removed"

clean-all:
	$(MAKE) clean ENV=dev
	$(MAKE) clean ENV=uat
	$(MAKE) clean ENV=prod
	minikube stop
