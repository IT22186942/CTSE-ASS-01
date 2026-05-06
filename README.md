# SmartCart CTSE Microservices Project

SmartCart is a prototype secure microservice-based ordering application for the CTSE cloud computing assignment. It contains four independently deployable services that communicate over HTTP:

- `auth-service`: user registration, login, and signed token validation.
- `catalog-service`: product catalog and stock reservation.
- `order-service`: order creation; integrates with auth, catalog, and notification.
- `notification-service`: queues user notifications and validates reads through auth.

The project includes Dockerfiles, Docker Compose, OpenAPI endpoints, GitHub Actions CI/CD, security scans, Azure Container Apps deployment templates, Kubernetes manifests, a report draft, and a 10-minute demo guide.

## Run Locally

```powershell
docker compose up --build
```

Service URLs:

- Auth: `http://localhost:8001`
- Catalog: `http://localhost:8002`
- Order: `http://localhost:8003`
- Notification: `http://localhost:8004`

Each service exposes:

- `GET /health`
- `GET /openapi.json`

## Demo Flow

Login with the seeded demo user:

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

Create an order. This validates the token in `auth-service`, reads and reserves stock in `catalog-service`, then queues a notification in `notification-service`.

```powershell
Invoke-RestMethod -Method Post http://localhost:8003/orders `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"product_id":"sku-keyboard","quantity":1}'
```

Read notifications:

```powershell
Invoke-RestMethod http://localhost:8004/notifications `
  -Headers @{ Authorization = "Bearer $token" }
```

## Test

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall shared services tests
```

## Repository Map

```text
services/                 Four independently deployable microservices
shared/                   Small standard-library HTTP utilities
tests/                    Unit and contract tests
deploy/                   Azure Container Apps and Kubernetes deployment files
diagrams/                 Mermaid architecture diagram
docs/report.md            Assignment report draft
docs/demo-guide.md        10-minute viva demonstration script
.github/workflows/        CI/CD and DevSecOps pipeline
```

## Cloud Deployment

The recommended cloud target is Azure Container Apps because it is simple, managed, and suitable for free-tier demos. The GitHub Actions workflow publishes images to GitHub Container Registry and can deploy `deploy/azure-container-apps.bicep` when Azure secrets are configured.

Required GitHub secrets for deployment:

- `AZURE_CREDENTIALS`
- `AZURE_RESOURCE_GROUP`
- `TOKEN_SECRET`
- `INTERNAL_API_KEY`
- Optional: `SNYK_TOKEN`
