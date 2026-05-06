import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.auth = load_module("auth_app", "services/auth-service/app.py")

    def test_token_round_trip(self):
        user = self.auth.create_user("alice@example.com", "Password123", "Alice")
        token = self.auth.sign({"sub": user["id"], "email": user["email"], "iat": self.auth.now_iso()})
        self.assertEqual(self.auth.verify(token)["email"], "alice@example.com")

    def test_tampered_token_is_rejected(self):
        user = self.auth.create_user("bob@example.com", "Password123", "Bob")
        token = self.auth.sign({"sub": user["id"], "email": user["email"], "iat": self.auth.now_iso()})
        self.assertIsNone(self.auth.verify(token + "bad"))


class CatalogServiceTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_module("catalog_app", "services/catalog-service/app.py")

    def test_reserve_stock_reduces_inventory(self):
        before = self.catalog.PRODUCTS["sku-keyboard"]["stock"]
        ok, product = self.catalog.reserve_stock("sku-keyboard", 2)
        self.assertTrue(ok)
        self.assertEqual(product["stock"], before - 2)

    def test_reserve_stock_rejects_missing_product(self):
        ok, message = self.catalog.reserve_stock("missing", 1)
        self.assertFalse(ok)
        self.assertEqual(message, "Product not found")


class ContractTests(unittest.TestCase):
    def test_each_service_exposes_openapi_metadata(self):
        services = {
            "auth": "services/auth-service/app.py",
            "catalog": "services/catalog-service/app.py",
            "order": "services/order-service/app.py",
            "notification": "services/notification-service/app.py",
        }
        for name, path in services.items():
            with self.subTest(service=name):
                module = load_module(f"{name}_app", path)
                self.assertEqual(module.OPENAPI["openapi"], "3.0.3")
                self.assertGreaterEqual(len(module.OPENAPI["paths"]), 2)


if __name__ == "__main__":
    unittest.main()
