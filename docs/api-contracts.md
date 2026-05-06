# API Contracts

Each service exposes an OpenAPI 3.0 contract at runtime:

- `auth-service`: `GET /openapi.json`
- `catalog-service`: `GET /openapi.json`
- `order-service`: `GET /openapi.json`
- `notification-service`: `GET /openapi.json`

Local URLs:

- `http://localhost:8001/openapi.json`
- `http://localhost:8002/openapi.json`
- `http://localhost:8003/openapi.json`
- `http://localhost:8004/openapi.json`

The most important integration contract is `POST /orders` in `order-service`. It requires an `Authorization: Bearer <token>` header and a JSON body:

```json
{
  "product_id": "sku-keyboard",
  "quantity": 1
}
```

Successful response:

```json
{
  "order": {
    "id": "generated-order-id",
    "user_id": "authenticated-user-id",
    "product_id": "sku-keyboard",
    "product_name": "Mechanical Keyboard",
    "quantity": 1,
    "unit_price": 89.99,
    "total": 89.99,
    "status": "confirmed",
    "created_at": "2026-05-06T00:00:00Z"
  },
  "stock": {
    "id": "sku-keyboard",
    "stock": 11
  },
  "notification": {
    "status": 201,
    "body": {}
  }
}
```

