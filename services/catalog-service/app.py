import os
import sys
import uuid
from http import HTTPStatus

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.http_utils import JsonHandler, env, error, now_iso, read_json, require_api_key, run, service_request, write_json


SERVICE = "catalog-service"
NOTIFICATION_URL = env("NOTIFICATION_SERVICE_URL", "")
INTERNAL_API_KEY = env("INTERNAL_API_KEY", "dev-internal-key")

PRODUCTS = {
    "sku-keyboard": {
        "id": "sku-keyboard",
        "name": "Mechanical Keyboard",
        "description": "Hot-swappable compact keyboard for developers.",
        "price": 89.99,
        "stock": 12,
        "created_at": now_iso(),
    },
    "sku-mouse": {
        "id": "sku-mouse",
        "name": "Wireless Mouse",
        "description": "Low-latency mouse with USB-C charging.",
        "price": 39.5,
        "stock": 20,
        "created_at": now_iso(),
    },
}


def list_products(handler):
    write_json(handler, 200, {"products": list(PRODUCTS.values())})


def get_product(handler):
    product = PRODUCTS.get(handler.path_id)
    if not product:
        error(handler, HTTPStatus.NOT_FOUND, "Product not found")
        return
    write_json(handler, 200, {"product": product})


def create_product(handler):
    if not require_api_key(handler):
        return
    data = read_json(handler)
    name = str(data.get("name", "")).strip()
    price = data.get("price")
    stock = data.get("stock", 0)
    if not name or price is None:
        error(handler, HTTPStatus.BAD_REQUEST, "Product name and price are required")
        return
    product_id = str(data.get("id") or f"sku-{uuid.uuid4().hex[:8]}")
    product = {
        "id": product_id,
        "name": name,
        "description": str(data.get("description", "")),
        "price": float(price),
        "stock": int(stock),
        "created_at": now_iso(),
    }
    PRODUCTS[product_id] = product
    if NOTIFICATION_URL:
        service_request(
            "POST",
            f"{NOTIFICATION_URL}/notifications",
            {
                "user_id": env("ADMIN_USER_ID", "catalog-admin"),
                "channel": "ops",
                "subject": "Catalog item created",
                "message": f"{product['name']} is now available in the catalog.",
            },
            api_key=INTERNAL_API_KEY,
        )
    write_json(handler, HTTPStatus.CREATED, {"product": product})


def reserve_stock(product_id, quantity):
    product = PRODUCTS.get(product_id)
    if not product:
        return False, "Product not found"
    if product["stock"] < quantity:
        return False, "Insufficient stock"
    product["stock"] -= quantity
    return True, product


def reserve_product(handler):
    if not require_api_key(handler):
        return
    data = read_json(handler)
    product_id = str(data.get("product_id", ""))
    quantity = int(data.get("quantity", 0))
    if quantity <= 0:
        error(handler, HTTPStatus.BAD_REQUEST, "Quantity must be greater than zero")
        return
    ok, result = reserve_stock(product_id, quantity)
    if not ok:
        error(handler, HTTPStatus.CONFLICT, result)
        return
    write_json(handler, 200, {"reserved": True, "product": result})


OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "SmartCart Catalog Service", "version": "1.0.0"},
    "paths": {
        "/health": {"get": {"summary": "Health check"}},
        "/products": {
            "get": {"summary": "List products"},
            "post": {"summary": "Create a product with an internal API key"},
        },
        "/products/{id}": {"get": {"summary": "Get product details"}},
        "/catalog/reservations": {"post": {"summary": "Reserve product stock for an order"}},
    },
}


class CatalogHandler(JsonHandler):
    service_name = SERVICE
    openapi = OPENAPI
    routes = {
        ("GET", "/products"): list_products,
        ("POST", "/products"): create_product,
        ("GET", "/products/{id}"): get_product,
        ("POST", "/catalog/reservations"): reserve_product,
    }


if __name__ == "__main__":
    run(CatalogHandler, 8002)
