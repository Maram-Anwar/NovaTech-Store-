from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import secrets
import threading
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from admin_manager import AdminManager
from cart_manager import CartManager
from cart_service import CartService
from checkout_service import CheckoutService
from config import my_email, my_password
from image_manager import ImageManager
from product_manager import ProductManager
from product_service import ProductService
from profile_manager import ProfileManager
from user_manager import UserManager
from wallet_manager import WalletManager


BASE_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 5055

# Always run with project files as the working directory so the existing
# managers keep reading/writing their original relative JSON paths.
os.chdir(BASE_DIR)

user_manager = UserManager("users.json")
admin_manager = AdminManager("admins.json")
product_manager = ProductManager("products.json")
image_manager = ImageManager("images/products")
cart_manager = CartManager("carts.json")
profile_manager = ProfileManager(user_manager)
wallet_manager = WalletManager(user_manager)
product_service = ProductService(product_manager, image_manager)
cart_service = CartService(cart_manager, product_manager)
checkout_service = CheckoutService(cart_service, product_manager, wallet_manager)

TOKENS: dict[str, dict] = {}
TOKEN_LOCK = threading.Lock()


# -----------------------------
# Helpers
# -----------------------------

def issue_token(role: str, identity: dict) -> str:
    token = secrets.token_urlsafe(32)
    with TOKEN_LOCK:
        TOKENS[token] = {"role": role, **identity}
    return token


def get_token_info(headers) -> dict | None:
    auth = headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    return TOKENS.get(token)


def clean_filename(name: str) -> str:
    name = Path(name or "image.jpg").name
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(name).stem)[:50] or "image"
    ext = Path(name).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    return stem + ext


def save_data_url_to_temp(image: dict | None) -> Path | None:
    if not image:
        return None
    data_url = str(image.get("data_url", ""))
    if not data_url.startswith("data:image/") or "," not in data_url:
        raise ValueError("Invalid image data")

    _, encoded = data_url.split(",", 1)
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("Invalid image encoding") from exc

    # Keep uploads bounded so large files cannot exhaust memory.
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Image must be 8 MB or smaller")

    temp_dir = BASE_DIR / ".tmp_uploads"
    temp_dir.mkdir(exist_ok=True)
    filename = f"{secrets.token_hex(8)}_{clean_filename(image.get('name', 'image.jpg'))}"
    path = temp_dir / filename
    path.write_bytes(raw)
    return path


def cleanup_temp(path: Path | None):
    if path:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


def sync_cart_username(old_username: str, new_username: str):
    old_username = old_username.strip().lower()
    new_username = new_username.strip().lower()
    for cart in cart_manager.carts:
        if cart.get("username", "").strip().lower() == old_username:
            cart["username"] = new_username
            cart_manager._save()
            return


def delete_user_cart(user_name: str):
    clean_name = user_name.strip().lower()
    original_length = len(cart_manager.carts)
    cart_manager.carts = [
        cart
        for cart in cart_manager.carts
        if cart.get("username", "").strip().lower() != clean_name
    ]
    if len(cart_manager.carts) != original_length:
        cart_manager._save()


def rename_token_user(old_name: str, new_name: str):
    with TOKEN_LOCK:
        for info in TOKENS.values():
            if info.get("role") == "user" and info.get("user_name", "").lower() == old_name.lower():
                info["user_name"] = new_name


def revoke_user_tokens(user_name: str):
    with TOKEN_LOCK:
        doomed = [
            token
            for token, info in TOKENS.items()
            if info.get("role") == "user" and info.get("user_name", "").lower() == user_name.lower()
        ]
        for token in doomed:
            TOKENS.pop(token, None)


def result_status(result: dict) -> int:
    if result.get("status") == "success":
        return 200
    message = str(result.get("message", "")).lower()
    if "not found" in message:
        return 404
    if "already exists" in message:
        return 409
    if "password" in message and ("wrong" in message or "incorrect" in message):
        return 401
    return 400


def string_result(message: str, success_messages: set[str] | None = None):
    success_messages = success_messages or set()
    ok = message in success_messages or "Successfully" in message or "Added To Cart" in message or "Cart Updated" in message
    return {
        "status": "success" if ok else "error",
        "message": message,
    }


def product_for_frontend(product: dict) -> dict:
    item = dict(product)
    images = []
    for image in item.get("images", []):
        image_copy = dict(image)
        path = str(image_copy.get("path", "")).replace("\\", "/")
        if path:
            image_copy["url"] = "/" + path.lstrip("/")
        images.append(image_copy)
    item["images"] = images
    return item


def current_user(headers):
    info = get_token_info(headers)
    if not info or info.get("role") != "user":
        return None
    return info


def current_admin(headers):
    info = get_token_info(headers)
    if not info or info.get("role") != "admin":
        return None
    return info


def storage_health():
    files = {
        "users": BASE_DIR / "users.json",
        "admins": BASE_DIR / "admins.json",
        "products": BASE_DIR / "products.json",
        "carts": BASE_DIR / "carts.json",
    }
    checks = {}
    healthy = True
    for key, path in files.items():
        item = {"exists": path.exists(), "readable": False, "writable": False, "valid_json": False}
        try:
            if path.exists():
                json.loads(path.read_text(encoding="utf-8"))
                item["readable"] = True
                item["valid_json"] = True
                item["writable"] = os.access(path, os.W_OK)
        except Exception as exc:
            item["error"] = str(exc)
        checks[key] = item
        healthy = healthy and all(item.get(k, False) for k in ("exists", "readable", "writable", "valid_json"))
    return healthy, checks


class StoreHandler(SimpleHTTPRequestHandler):
    server_version = "NovaTechStore/6.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format, *args):
        print("[HTTP]", format % args)

    # ---------- response helpers ----------
    def send_json(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        # Allow the frontend to call this API even when opened with
        # VS Code Live Server or directly from the local filesystem.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 12 * 1024 * 1024:
            raise ValueError("Request too large")
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Invalid JSON body") from exc

    def require_user(self):
        info = current_user(self.headers)
        if not info:
            self.send_json({"status": "error", "message": "User Login Required"}, 401)
        return info

    def require_admin(self):
        info = current_admin(self.headers)
        if not info:
            self.send_json({"status": "error", "message": "Admin Login Required"}, 401)
        return info

    # ---------- HTTP verbs ----------
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path.startswith("/api"):
            try:
                return self.handle_api_get(path, query)
            except Exception as exc:
                print("GET API ERROR:", repr(exc))
                return self.send_json({"status": "error", "message": "Internal Server Error"}, 500)

        # Only expose frontend assets and product images. Backend source files
        # and JSON storage must never be downloadable from the web server.
        if path == "/":
            self.path = "/index.html"
            return super().do_GET()

        allowed_files = {"/index.html", "/styles.css", "/app.js"}
        if path in allowed_files or path.startswith("/images/products/"):
            return super().do_GET()

        return self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            data = self.read_json()
            return self.handle_api_post(path, data)
        except ValueError as exc:
            return self.send_json({"status": "error", "message": str(exc)}, 400)
        except Exception as exc:
            print("POST API ERROR:", repr(exc))
            return self.send_json({"status": "error", "message": "Internal Server Error"}, 500)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            data = self.read_json()
            return self.handle_api_patch(path, data)
        except ValueError as exc:
            return self.send_json({"status": "error", "message": str(exc)}, 400)
        except Exception as exc:
            print("PATCH API ERROR:", repr(exc))
            return self.send_json({"status": "error", "message": "Internal Server Error"}, 500)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            data = self.read_json()
            return self.handle_api_delete(path, data)
        except ValueError as exc:
            return self.send_json({"status": "error", "message": str(exc)}, 400)
        except Exception as exc:
            print("DELETE API ERROR:", repr(exc))
            return self.send_json({"status": "error", "message": "Internal Server Error"}, 500)

    # ---------- GET ----------
    def handle_api_get(self, path, query):
        if path == "/api/health":
            healthy, checks = storage_health()
            # Keep the public health response intentionally minimal.
            # Detailed storage checks stay server-side and are never exposed
            # to unauthenticated visitors.
            if not healthy:
                print("[HEALTH] Storage check failed:", checks)
            payload = {
                "status": "success" if healthy else "error",
                "message": "Service ready" if healthy else "Service unavailable",
                "storage_ready": healthy,
                "version": "6.0",
            }
            return self.send_json(payload, 200 if healthy else 500)

        if path == "/api/products":
            products = product_manager.get_all_products()
            keyword = (query.get("search", [""])[0] or "").strip()
            category = (query.get("category", [""])[0] or "").strip()
            if keyword:
                products = product_manager.search_products(keyword)
            if category:
                products = [p for p in products if p.get("category", "").lower() == category.lower()]
            return self.send_json({
                "status": "success",
                "products": [product_for_frontend(p) for p in products],
            })

        if path == "/api/categories":
            return self.send_json({"status": "success", "categories": product_manager.get_categories()})

        if path == "/api/me":
            info = self.require_user()
            if not info:
                return
            result = profile_manager.get_profile(info["user_name"])
            return self.send_json(result, result_status(result))

        if path == "/api/wallet":
            info = self.require_user()
            if not info:
                return
            result = wallet_manager.get_balance(info["user_name"])
            return self.send_json(result, result_status(result))

        if path == "/api/cart":
            info = self.require_user()
            if not info:
                return
            result = cart_service.get_cart_view(info["user_name"])
            if isinstance(result, dict) and result.get("status") == "error":
                return self.send_json(result, 400)
            for item in result.get("items", []):
                if item.get("main_image"):
                    item["main_image_url"] = "/" + str(item["main_image"]).lstrip("/")
            result["status"] = "success"
            return self.send_json(result)

        if path == "/api/admin/stats":
            if not self.require_admin():
                return
            statistics = product_manager.get_statistics()
            statistics["total_users"] = len(user_manager.database)
            return self.send_json({"status": "success", "statistics": statistics})

        if path == "/api/admin/low-stock":
            if not self.require_admin():
                return
            try:
                limit = int(query.get("limit", ["5"])[0])
            except ValueError:
                limit = 5
            products = product_manager.get_low_stock_products(limit)
            return self.send_json({"status": "success", "products": [product_for_frontend(p) for p in products]})

        if path == "/api/admin/users":
            if not self.require_admin():
                return
            result = user_manager.get_all_users()
            return self.send_json(result, result_status(result))

        return self.send_json({"status": "error", "message": "Endpoint Not Found"}, 404)

    # ---------- POST ----------
    def handle_api_post(self, path, data):
        if path == "/api/auth/login":
            result = user_manager.login(data.get("email", ""), data.get("password", ""))
            if result.get("status") != "success":
                return self.send_json(result, result_status(result))
            user = result["user"]
            token = issue_token("user", {"user_name": user["user_name"], "email": user["email"]})
            return self.send_json({**result, "token": token, "role": "user"})

        if path == "/api/auth/admin-login":
            result = admin_manager.login(data.get("email", ""), data.get("password", ""))
            if result.get("status") != "success":
                return self.send_json(result, result_status(result))
            admin = result["admin"]
            token = issue_token("admin", {"user_name": admin["user_name"], "email": admin["email"]})
            return self.send_json({**result, "token": token, "role": "admin"})

        if path == "/api/auth/register":
            result = user_manager.register(
                data.get("user_name", ""),
                data.get("password", ""),
                data.get("email", ""),
            )
            return self.send_json(result, 200 if result.get("status") == "pending" else result_status(result))

        if path == "/api/auth/resend-otp":
            result = user_manager.resend_otp(data.get("email", ""))
            return self.send_json(result, 200 if result.get("status") == "pending" else result_status(result))

        if path == "/api/auth/verify-otp":
            email = data.get("email", "")
            result = user_manager.verify_otp(email, data.get("otp", ""))
            if result.get("status") != "success":
                return self.send_json(result, result_status(result))
            user = result["user"]
            token = issue_token("user", {"user_name": user["user_name"], "email": user["email"]})
            return self.send_json({**result, "token": token, "role": "user"})

        if path == "/api/auth/logout":
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                with TOKEN_LOCK:
                    TOKENS.pop(auth[7:].strip(), None)
            return self.send_json({"status": "success", "message": "Logged Out"})

        if path == "/api/cart":
            info = self.require_user()
            if not info:
                return
            message = cart_service.add_product_to_cart(info["user_name"], data.get("product_id"), data.get("quantity", 1))
            result = string_result(message)
            return self.send_json(result, 200 if result["status"] == "success" else 400)

        if path == "/api/checkout":
            info = self.require_user()
            if not info:
                return
            result = checkout_service.checkout(info["user_name"])
            return self.send_json(result, result_status(result))

        if path == "/api/admin/wallet/add":
            if not self.require_admin():
                return
            result = wallet_manager.add_balance(data.get("user_name", ""), data.get("amount"))
            return self.send_json(result, result_status(result))

        if path == "/api/admin/products":
            if not self.require_admin():
                return
            name = str(data.get("name", ""))
            category = str(data.get("category", ""))
            try:
                price = float(data.get("price"))
                quantity = int(data.get("quantity"))
            except (TypeError, ValueError):
                return self.send_json({"status": "error", "message": "Invalid Price Or Quantity"}, 400)

            temp = None
            try:
                temp = save_data_url_to_temp(data.get("image"))
                sources = [str(temp)] if temp else []
                message = product_service.add_product(
                    name, category, price, quantity, sources,
                    brand=data.get("brand", "Nova"),
                    description=data.get("description", ""),
                    rating=data.get("rating", 4.5),
                    badge=data.get("badge", "New"),
                )
            except ValueError as exc:
                return self.send_json({"status": "error", "message": str(exc)}, 400)
            finally:
                cleanup_temp(temp)

            result = string_result(message, {"Product Added Successfully"})
            return self.send_json(result, 201 if result["status"] == "success" else 400)

        match = re.fullmatch(r"/api/admin/products/(\d+)/main-image", path)
        if match:
            if not self.require_admin():
                return
            product_id = int(match.group(1))
            temp = None
            try:
                temp = save_data_url_to_temp(data.get("image"))
                if not temp:
                    return self.send_json({"status": "error", "message": "Image Is Required"}, 400)
                message = product_service.replace_main_image(product_id, str(temp))
            except ValueError as exc:
                return self.send_json({"status": "error", "message": str(exc)}, 400)
            finally:
                cleanup_temp(temp)
            result = string_result(message, {"Main Image Updated Successfully", "Main Image Updated Successfully, But Old Image Cleanup Failed"})
            return self.send_json(result, 200 if result["status"] == "success" else 400)

        return self.send_json({"status": "error", "message": "Endpoint Not Found"}, 404)

    # ---------- PATCH ----------
    def handle_api_patch(self, path, data):
        if path == "/api/profile/username":
            info = self.require_user()
            if not info:
                return
            old_name = info["user_name"]
            new_name = str(data.get("new_name", "")).strip()
            result = profile_manager.update_username(old_name, new_name)
            if result.get("status") == "success":
                sync_cart_username(old_name, new_name)
                rename_token_user(old_name, new_name)
                result["user_name"] = new_name
            return self.send_json(result, result_status(result))

        if path == "/api/profile/password":
            info = self.require_user()
            if not info:
                return
            result = profile_manager.change_password(
                info["user_name"],
                str(data.get("old_password", "")),
                str(data.get("new_password", "")),
            )
            return self.send_json(result, result_status(result))

        match = re.fullmatch(r"/api/cart/(\d+)", path)
        if match:
            info = self.require_user()
            if not info:
                return
            message = cart_service.update_product_quantity(info["user_name"], int(match.group(1)), data.get("quantity"))
            result = string_result(message, {"Product Quantity Updated Successfully"})
            return self.send_json(result, 200 if result["status"] == "success" else 400)

        match = re.fullmatch(r"/api/admin/products/(\d+)", path)
        if match:
            if not self.require_admin():
                return
            product_id = int(match.group(1))
            kwargs = {}
            for field in ("name", "category", "brand", "description", "badge"):
                if field in data:
                    kwargs[field] = str(data[field])
            try:
                if "price" in data:
                    kwargs["price"] = float(data["price"])
                if "quantity" in data:
                    kwargs["quantity"] = int(data["quantity"])
                if "rating" in data:
                    kwargs["rating"] = float(data["rating"])
            except (TypeError, ValueError):
                return self.send_json({"status": "error", "message": "Invalid Price, Quantity Or Rating"}, 400)
            message = product_manager.update_product(product_id, **kwargs)
            result = string_result(message, {"Product Updated Successfully"})
            return self.send_json(result, 200 if result["status"] == "success" else 400)

        return self.send_json({"status": "error", "message": "Endpoint Not Found"}, 404)

    # ---------- DELETE ----------
    def handle_api_delete(self, path, data):
        if path == "/api/profile":
            info = self.require_user()
            if not info:
                return
            user_name = info["user_name"]
            result = profile_manager.delete_my_account(user_name, str(data.get("password", "")))
            if result.get("status") != "success":
                return self.send_json(result, result_status(result))

            nested = result.get("message")
            if isinstance(nested, dict) and nested.get("status") != "success":
                return self.send_json(nested, result_status(nested))

            delete_user_cart(user_name)
            revoke_user_tokens(user_name)
            message = nested.get("message", "User Deleted Successfully") if isinstance(nested, dict) else str(nested)
            return self.send_json({"status": "success", "message": message})

        if path == "/api/cart":
            info = self.require_user()
            if not info:
                return
            message = cart_service.clear_user_cart(info["user_name"])
            result = string_result(message, {"Cart Cleared Successfully", "Cart Not Found"})
            if message == "Cart Not Found":
                result = {"status": "success", "message": "Cart Already Empty"}
            return self.send_json(result)

        match = re.fullmatch(r"/api/cart/(\d+)", path)
        if match:
            info = self.require_user()
            if not info:
                return
            message = cart_service.remove_product_from_cart(info["user_name"], int(match.group(1)))
            result = string_result(message, {"Product Removed From Cart"})
            return self.send_json(result, 200 if result["status"] == "success" else 400)

        match = re.fullmatch(r"/api/admin/products/(\d+)", path)
        if match:
            if not self.require_admin():
                return
            message = product_service.delete_product(int(match.group(1)))
            result = string_result(message, {"Product Deleted Successfully"})
            return self.send_json(result, 200 if result["status"] == "success" else 400)

        return self.send_json({"status": "error", "message": "Endpoint Not Found"}, 404)


def open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}")


def main():
    server = ThreadingHTTPServer((HOST, PORT), StoreHandler)
    print("=" * 58)
    print(" NOVA TECH STORE IS RUNNING")
    print(f" http://{HOST}:{PORT}")
    healthy, checks = storage_health()
    if healthy:
        print(" Backend + frontend are connected to writable JSON storage.")
        print(f" Data loaded: {len(user_manager.database)} users | {len(admin_manager.database)} admins | {len(product_manager.database)} products")
    else:
        print(" WARNING: One or more JSON files cannot be read/written.")
        for name, check in checks.items():
            print(f"  - {name}: {check}")
    if not admin_manager.database:
        print(" Admin account not configured. Run: python setup_admin.py")
    print(" Press Ctrl+C to stop.")
    print("=" * 58)

    threading.Timer(0.7, open_browser).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
