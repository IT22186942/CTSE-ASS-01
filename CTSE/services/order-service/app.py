import os
import sys
import uuid
from http import HTTPStatus

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.http_utils import (
    JsonHandler,
    bearer_token,
    env,
    error,
    now_iso,
    query,
    read_json,
    run,
    service_request,
    write_json,
)


SERVICE = "order-service"
AUTH_URL = env("AUTH_SERVICE_URL", "http://auth-service:8001")
CATALOG_URL = env("CATALOG_SERVICE_URL", "http://catalog-service:8002")
NOTIFICATION_URL = env("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")
INTERNAL_API_KEY = env("INTERNAL_API_KEY", "dev-internal-key")

ORDERS = []


def validate_user(token):
    status, body = service_request("GET", f"{AUTH_URL}/auth/validate", token=token)
    if status == 200 and body.get("active"):
        return True, body["user"]
    return False, body


def get_product(product_id):
    status, body = service_request("GET", f"{CATALOG_URL}/products/{product_id}")
    if status == 200:
        return True, body["product"]
    return False, body


def reserve_stock(product_id, quantity):
    status, body = service_request(
        "POST",
        f"{CATALOG_URL}/catalog/reservations",
        {"product_id": product_id, "quantity": quantity},
        api_key=INTERNAL_API_KEY,
    )
    if status == 200:
        return True, body["product"]
    return False, body


def notify(user, order):
    status, body = service_request(
        "POST",
        f"{NOTIFICATION_URL}/notifications",
        {
            "user_id": user["id"],
            "channel": "email",
            "subject": "SmartCart order confirmed",
            "message": f"Order {order['id']} was placed for {order['quantity']} item(s).",
        },
        api_key=INTERNAL_API_KEY,
    )
    return status, body


def create_order(handler):
    token = bearer_token(handler)
    ok, user_or_error = validate_user(token)
    if not ok:
        error(handler, HTTPStatus.UNAUTHORIZED, "Token validation failed", user_or_error)
        return
    data = read_json(handler)
    product_id = str(data.get("product_id", ""))
    quantity = int(data.get("quantity", 0))
    if quantity <= 0:
        error(handler, HTTPStatus.BAD_REQUEST, "Quantity must be greater than zero")
        return
    ok, product_or_error = get_product(product_id)
    if not ok:
        error(handler, HTTPStatus.NOT_FOUND, "Product lookup failed", product_or_error)
        return
    ok, reserved_or_error = reserve_stock(product_id, quantity)
    if not ok:
        error(handler, HTTPStatus.CONFLICT, "Stock reservation failed", reserved_or_error)
        return
    product = product_or_error
    order = {
        "id": str(uuid.uuid4()),
        "user_id": user_or_error["id"],
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "total": round(float(product["price"]) * quantity, 2),
        "status": "confirmed",
        "created_at": now_iso(),
    }
    ORDERS.append(order)
    notification_status, notification_body = notify(user_or_error, order)
    write_json(
        handler,
        HTTPStatus.CREATED,
        {"order": order, "stock": reserved_or_error, "notification": {"status": notification_status, "body": notification_body}},
    )


def list_orders(handler):
    token = bearer_token(handler)
    ok, user_or_error = validate_user(token)
    if not ok:
        error(handler, HTTPStatus.UNAUTHORIZED, "Token validation failed", user_or_error)
        return
    user_id = (query(handler).get("user_id") or [user_or_error["id"]])[0]
    if user_id != user_or_error["id"]:
        error(handler, HTTPStatus.FORBIDDEN, "Users can only read their own orders")
        return
    write_json(handler, 200, {"orders": [item for item in ORDERS if item["user_id"] == user_id]})


OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "SmartCart Order Service", "version": "1.0.0"},
    "paths": {
        "/health": {"get": {"summary": "Health check"}},
        "/orders": {
            "get": {"summary": "List orders for authenticated user"},
            "post": {"summary": "Create an order by validating auth, catalog stock, and notifications"},
        },
    },
}


class OrderHandler(JsonHandler):
    service_name = SERVICE
    openapi = OPENAPI
    routes = {
        ("POST", "/orders"): create_order,
        ("GET", "/orders"): list_orders,
    }


if __name__ == "__main__":
    run(OrderHandler, 8003)
