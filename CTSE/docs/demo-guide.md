# 10-Minute Demonstration Guide

## 1. Show Architecture

Open `diagrams/architecture.mmd` or the diagram in `docs/report.md`. Explain that SmartCart has auth, catalog, order, and notification services running as independent containers.

## 2. Start the Prototype

```powershell
docker compose up --build
```

Confirm health checks:

```powershell
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8002/health
Invoke-RestMethod http://localhost:8003/health
Invoke-RestMethod http://localhost:8004/health
```

## 3. Show API Contracts

```powershell
Invoke-RestMethod http://localhost:8003/openapi.json
```

Mention that each service has its own `openapi.json`.

## 4. Demonstrate Inter-Service Communication

Login:

```powershell
$login = Invoke-RestMethod -Method Post http://localhost:8001/auth/login `
  -ContentType "application/json" `
  -Body '{"email":"demo@smartcart.local","password":"Password123"}'
$token = $login.token
```

List products:

```powershell
Invoke-RestMethod http://localhost:8002/products
```

Create an order:

```powershell
Invoke-RestMethod -Method Post http://localhost:8003/orders `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"product_id":"sku-keyboard","quantity":1}'
```

Explain that `order-service` called auth, catalog, and notification services.

Read notifications:

```powershell
Invoke-RestMethod http://localhost:8004/notifications `
  -Headers @{ Authorization = "Bearer $token" }
```

## 5. Show CI/CD and DevSecOps

Open `.github/workflows/ci-cd.yml` and explain:

- Unit tests run on pull requests.
- Trivy scans source and dependency files.
- Snyk runs when `SNYK_TOKEN` is configured.
- Docker images are pushed to GHCR on `main`.
- Azure Container Apps deployment runs when Azure secrets are present.

## 6. Show Cloud Deployment Files

Open `deploy/azure-container-apps.bicep`. Explain that the services are deployed as managed container apps, use secrets for sensitive values, and can scale down to reduce cost.

