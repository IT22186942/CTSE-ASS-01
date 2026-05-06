import json
import os
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def env(name, default):
    return os.environ.get(name, default)


def read_json(handler):
    length = int(handler.headers.get("content-length", "0") or "0")
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        raise ValueError("Request body must be valid JSON")


def write_json(handler, status, payload):
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("content-type", "application/json")
    handler.send_header("content-length", str(len(body)))
    handler.send_header("x-content-type-options", "nosniff")
    handler.send_header("cache-control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def error(handler, status, message, details=None):
    payload = {"error": message, "status": status}
    if details is not None:
        payload["details"] = details
    write_json(handler, status, payload)


def query(handler):
    return parse_qs(urlparse(handler.path).query)


def path(handler):
    return urlparse(handler.path).path


def bearer_token(handler):
    value = handler.headers.get("authorization", "")
    if value.lower().startswith("bearer "):
        return value.split(" ", 1)[1].strip()
    return ""


def require_api_key(handler):
    expected = env("INTERNAL_API_KEY", "dev-internal-key")
    supplied = handler.headers.get("x-api-key", "")
    if supplied != expected:
        error(handler, HTTPStatus.UNAUTHORIZED, "Missing or invalid internal API key")
        return False
    return True


def service_request(method, url, payload=None, token=None, api_key=None, timeout=3):
    data = None
    headers = {"accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"
    if token:
        headers["authorization"] = f"Bearer {token}"
    if api_key:
        headers["x-api-key"] = api_key
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"error": raw}
        return exc.code, body
    except Exception as exc:
        return 503, {"error": "Service unavailable", "details": str(exc)}


class JsonHandler(BaseHTTPRequestHandler):
    service_name = "service"
    routes = {}
    openapi = {}

    def log_message(self, format, *args):
        print(f"{self.service_name} - {format % args}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-methods", "GET,POST,OPTIONS")
        self.send_header("access-control-allow-headers", "authorization,content-type,x-api-key")
        self.end_headers()

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def dispatch(self, method):
        route = path(self)
        if route == "/health":
            write_json(self, 200, {"service": self.service_name, "status": "ok", "time": now_iso()})
            return
        if route == "/openapi.json":
            write_json(self, 200, self.openapi)
            return
        handler = self.routes.get((method, route))
        if handler:
            try:
                handler(self)
            except ValueError as exc:
                error(self, 400, str(exc))
            except Exception as exc:
                error(self, 500, "Unexpected service error", str(exc))
            return
        for (route_method, route_template), dynamic_handler in self.routes.items():
            if route_method == method and route_template.endswith("/{id}"):
                prefix = route_template[:-5]
                if route.startswith(prefix) and route[len(prefix):]:
                    self.path_id = route[len(prefix):].strip("/")
                    try:
                        dynamic_handler(self)
                    except ValueError as exc:
                        error(self, 400, str(exc))
                    except Exception as exc:
                        error(self, 500, "Unexpected service error", str(exc))
                    return
        error(self, 404, "Route not found")


def run(handler_class, default_port):
    port = int(env("PORT", str(default_port)))
    server = ThreadingHTTPServer(("0.0.0.0", port), handler_class)
    print(f"{handler_class.service_name} listening on port {port}")
    server.serve_forever()
