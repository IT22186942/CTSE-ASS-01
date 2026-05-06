import base64
import hashlib
import hmac
import json
import os
import sys
import uuid
from http import HTTPStatus

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.http_utils import JsonHandler, env, error, now_iso, read_json, run, service_request, write_json


SERVICE = "auth-service"
TOKEN_SECRET = env("TOKEN_SECRET", "change-me-in-cloud")
NOTIFICATION_URL = env("NOTIFICATION_SERVICE_URL", "")
INTERNAL_API_KEY = env("INTERNAL_API_KEY", "dev-internal-key")

USERS = {}


def hash_password(password, salt):
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def create_user(email, password, name):
    user_id = str(uuid.uuid4())
    salt = uuid.uuid4().hex
    USERS[email] = {
        "id": user_id,
        "email": email,
        "name": name,
        "salt": salt,
        "password_hash": hash_password(password, salt),
        "created_at": now_iso(),
    }
    return USERS[email]


def public_user(user):
    return {key: user[key] for key in ("id", "email", "name", "created_at")}


def sign(payload):
    body = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True).encode("utf-8")).decode("utf-8")
    signature = hmac.new(TOKEN_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def verify(token):
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(TOKEN_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    payload = json.loads(base64.urlsafe_b64decode(body.encode("utf-8")).decode("utf-8"))
    user = USERS.get(payload.get("email"))
    if not user or user["id"] != payload.get("sub"):
        return None
    return user


def register(handler):
    data = read_json(handler)
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    name = str(data.get("name", "")).strip()
    if not email or "@" not in email:
        error(handler, HTTPStatus.BAD_REQUEST, "A valid email is required")
        return
    if len(password) < 8:
        error(handler, HTTPStatus.BAD_REQUEST, "Password must be at least 8 characters")
        return
    if email in USERS:
        error(handler, HTTPStatus.CONFLICT, "User already exists")
        return
    user = create_user(email, password, name or email.split("@", 1)[0])
    if NOTIFICATION_URL:
        service_request(
            "POST",
            f"{NOTIFICATION_URL}/notifications",
            {
                "user_id": user["id"],
                "channel": "email",
                "subject": "Welcome to SmartCart",
                "message": f"Hello {user['name']}, your account is ready.",
            },
            api_key=INTERNAL_API_KEY,
        )
    write_json(handler, HTTPStatus.CREATED, {"user": public_user(user)})


def login(handler):
    data = read_json(handler)
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    user = USERS.get(email)
    if not user or user["password_hash"] != hash_password(password, user["salt"]):
        error(handler, HTTPStatus.UNAUTHORIZED, "Invalid email or password")
        return
    token = sign({"sub": user["id"], "email": user["email"], "iat": now_iso()})
    write_json(handler, 200, {"token": token, "user": public_user(user)})


def validate(handler):
    token = handler.headers.get("authorization", "").replace("Bearer ", "").strip()
    if not token:
        from shared.http_utils import query

        token = (query(handler).get("token") or [""])[0]
    user = verify(token)
    if not user:
        error(handler, HTTPStatus.UNAUTHORIZED, "Invalid token")
        return
    write_json(handler, 200, {"active": True, "user": public_user(user)})


OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "SmartCart Auth Service", "version": "1.0.0"},
    "paths": {
        "/health": {"get": {"summary": "Health check"}},
        "/auth/register": {"post": {"summary": "Create a user account"}},
        "/auth/login": {"post": {"summary": "Authenticate and return a signed token"}},
        "/auth/validate": {"get": {"summary": "Validate a bearer token"}},
    },
}


create_user("demo@smartcart.local", "Password123", "Demo User")


class AuthHandler(JsonHandler):
    service_name = SERVICE
    openapi = OPENAPI
    routes = {
        ("POST", "/auth/register"): register,
        ("POST", "/auth/login"): login,
        ("GET", "/auth/validate"): validate,
    }


if __name__ == "__main__":
    run(AuthHandler, 8001)
