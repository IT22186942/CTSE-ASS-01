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
    require_api_key,
    run,
    service_request,
    write_json,
)


SERVICE = "notification-service"
AUTH_URL = env("AUTH_SERVICE_URL", "")
INTERNAL_API_KEY = env("INTERNAL_API_KEY", "dev-internal-key")
NOTIFICATIONS = []


def validate_token(token):
    if not AUTH_URL:
        return True, {"id": "local-dev", "email": "local@smartcart.local", "name": "Local Dev"}
    status, body = service_request("GET", f"{AUTH_URL}/auth/validate", token=token)
    if status == 200 and body.get("active"):
        return True, body["user"]
    return False, body


def create_notification(handler):
    if not require_api_key(handler):
        return
    data = read_json(handler)
    required = ["user_id", "subject", "message"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        error(handler, HTTPStatus.BAD_REQUEST, "Missing required fields", missing)
        return
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": str(data["user_id"]),
        "channel": str(data.get("channel", "email")),
        "subject": str(data["subject"]),
        "message": str(data["message"]),
        "status": "queued",
        "created_at": now_iso(),
    }
    NOTIFICATIONS.append(notification)
    write_json(handler, HTTPStatus.CREATED, {"notification": notification})


def list_notifications(handler):
    token = bearer_token(handler)
    ok, result = validate_token(token)
    if not ok:
        error(handler, HTTPStatus.UNAUTHORIZED, "Token validation failed", result)
        return
    user_id = (query(handler).get("user_id") or [result["id"]])[0]
    if user_id != result["id"]:
        error(handler, HTTPStatus.FORBIDDEN, "Users can only read their own notifications")
        return
    matches = [item for item in NOTIFICATIONS if item["user_id"] == user_id]
    write_json(handler, 200, {"notifications": matches})


OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "SmartCart Notification Service", "version": "1.0.0"},
    "paths": {
        "/health": {"get": {"summary": "Health check"}},
        "/notifications": {
            "get": {"summary": "List notifications for the authenticated user"},
            "post": {"summary": "Queue a notification from another service"},
        },
    },
}


class NotificationHandler(JsonHandler):
    service_name = SERVICE
    openapi = OPENAPI
    routes = {
        ("POST", "/notifications"): create_notification,
        ("GET", "/notifications"): list_notifications,
    }


if __name__ == "__main__":
    run(NotificationHandler, 8004)
