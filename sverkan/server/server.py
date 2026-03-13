import socket
"""
Sverkan Backend Server (Fresh)
Accounts stored as JSON in /accounts/admin and /accounts/students
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, List
from flask import Flask, request, redirect, session, jsonify
import subprocess
import ctypes
from ctypes import wintypes
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
ACCOUNTS_DIR = os.path.join(PROJECT_ROOT, "accounts")
ADMIN_DIR = os.path.join(ACCOUNTS_DIR, "admin")
STUDENTS_DIR = os.path.join(ACCOUNTS_DIR, "students")
SCHEMA_PATH = os.path.join(ACCOUNTS_DIR, "_schema.json")
APP_REGISTRY_PATH = os.path.join(PROJECT_ROOT, "server", "apps_registry.json")

APP_PORT = int(os.getenv("APP_PORT", 4272))
PUBLIC_SERVER_ADDRESS = "sverkan.oscyra.solutions"
SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret-change-in-production")

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path="",
    template_folder=FRONTEND_DIR,
)
app.secret_key = SECRET_KEY
CORS(app, origins=[
    "https://sverkan.oscyra.solutions",
    "https://csh.oscyra.solutions",
    "https://oscyra.solutions",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
])

RUNNING_APPS = {}


def _bring_process_to_front(pid: int) -> bool:
    if os.name != "nt":
        return False

    user32 = ctypes.windll.user32

    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    IsWindowVisible = user32.IsWindowVisible
    ShowWindow = user32.ShowWindow
    SetForegroundWindow = user32.SetForegroundWindow

    hwnds = []

    def callback(hwnd, lparam):
        if not IsWindowVisible(hwnd):
            return True
        proc_id = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value == pid:
            hwnds.append(hwnd)
            return False
        return True

    EnumWindows(EnumWindowsProc(callback), 0)

    if not hwnds:
        return False

    hwnd = hwnds[0]
    SW_RESTORE = 9
    ShowWindow(hwnd, SW_RESTORE)
    return bool(SetForegroundWindow(hwnd))


def _close_process_window(pid: int) -> bool:
    if os.name != "nt":
        return False

    user32 = ctypes.windll.user32

    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    PostMessageW = user32.PostMessageW
    IsWindowVisible = user32.IsWindowVisible

    hwnds = []

    def callback(hwnd, lparam):
        if not IsWindowVisible(hwnd):
            return True
        proc_id = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value == pid:
            hwnds.append(hwnd)
            return False
        return True

    EnumWindows(EnumWindowsProc(callback), 0)

    if not hwnds:
        return False

    WM_CLOSE = 0x0010
    PostMessageW(hwnds[0], WM_CLOSE, 0, 0)
    return True


DEFAULT_APP_REGISTRY = {
    "skola": {
        "app_id": "skola",
        "app_name": "Skola",
        "app_icon": "📚",
        "app_path": "/skola-app",
        "app_color": "#4ba3ff",
    },
    "klar": {
        "app_id": "klar",
        "app_name": "Klar",
        "app_icon": "🌐",
        "app_path": None,
        "app_color": "#5fd4b0",
    },
    "word": {
        "app_id": "word",
        "app_name": "Word",
        "app_icon": "📄",
        "app_path": None,
        "app_color": "#2b579a",
    },
    "excel": {
        "app_id": "excel",
        "app_name": "Excel",
        "app_icon": "📊",
        "app_path": None,
        "app_color": "#217346",
    },
    "powerpoint": {
        "app_id": "powerpoint",
        "app_name": "PowerPoint",
        "app_icon": "📽️",
        "app_path": None,
        "app_color": "#d24726",
    },
    "publisher": {
        "app_id": "publisher",
        "app_name": "Publisher",
        "app_icon": "📰",
        "app_path": None,
        "app_color": "#077568",
    },
    "admin_panel": {
        "app_id": "admin_panel",
        "app_name": "Adminpanel",
        "app_icon": "👥",
        "app_path": "/admin",
        "app_color": "#ff6b6b",
    },
}

DEFAULT_STUDENT_APPS = ["skola", "klar", "word", "excel", "powerpoint", "publisher"]
DEFAULT_ADMIN_APPS = ["admin_panel", "skola", "klar"]


def _load_app_registry():
    if os.path.exists(APP_REGISTRY_PATH):
        try:
            return _load_json(APP_REGISTRY_PATH)
        except Exception:
            return {}
    return {}


def _save_app_registry(registry: dict):
    _save_json(APP_REGISTRY_PATH, registry)


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or f"app-{uuid4().hex[:6]}"


def _detect_office_apps():
    candidates = [
        ("word", "Word", "📄", "WINWORD.EXE", "#2b579a"),
        ("excel", "Excel", "📊", "EXCEL.EXE", "#217346"),
        ("powerpoint", "PowerPoint", "📽️", "POWERPNT.EXE", "#d24726"),
        ("publisher", "Publisher", "📰", "MSPUB.EXE", "#077568"),
        ("onenote", "OneNote", "📒", "ONENOTE.EXE", "#80397B"),
    ]

    roots = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    ]

    office_paths = [
        os.path.join(root, "Microsoft Office", "root", "Office16") for root in roots
    ] + [
        os.path.join(root, "Microsoft Office", "Office16") for root in roots
    ]

    detected = {}
    for app_id, name, icon, exe, color in candidates:
        for base in office_paths:
            path = os.path.join(base, exe)
            if os.path.exists(path):
                detected[app_id] = {
                    "app_id": app_id,
                    "app_name": name,
                    "app_icon": icon,
                    "app_path": path,
                    "app_color": color,
                }
                break

    return detected


def _ensure_app_registry():
    registry = _load_app_registry()
    updated = False

    for app_id, app in DEFAULT_APP_REGISTRY.items():
        if app_id not in registry:
            registry[app_id] = app
            updated = True

    detected = _detect_office_apps()
    for app_id, app in detected.items():
        if app_id not in registry:
            registry[app_id] = app
            updated = True

    if updated:
        _save_app_registry(registry)
    return registry


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _ensure_dirs():
    os.makedirs(ADMIN_DIR, exist_ok=True)
    os.makedirs(STUDENTS_DIR, exist_ok=True)


def _role_to_dir(role: str) -> str:
    if role == "admin":
        return ADMIN_DIR
    elif role == "mcu":
        return os.path.join(ACCOUNTS_DIR, "mcu")
    else:
        return STUDENTS_DIR


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _list_account_files():
    files = []
    for folder in (ADMIN_DIR, STUDENTS_DIR, os.path.join(ACCOUNTS_DIR, "mcu")):
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                if name.lower().endswith(".json"):
                    files.append(os.path.join(folder, name))
    return files


def _load_accounts():
    accounts = {}
    for path in _list_account_files():
        try:
            data = _load_json(path)
            accounts[data.get("username")] = data
        except Exception:
            continue
    return accounts


def _find_account(username: str):
    accounts = _load_accounts()
    return accounts.get(username)


def _save_account(account: dict, previous_role: Optional[str] = None):
    role = account.get("role", "student")
    target_dir = _role_to_dir(role)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"{account['username']}.json"
    target_path = os.path.join(target_dir, filename)

    if previous_role and previous_role != role:
        old_dir = _role_to_dir(previous_role)
        old_path = os.path.join(old_dir, filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    _save_json(target_path, account)


def _default_account_schema():
    return {
        "id": "user-uuid",
        "username": "string",
        "password_hash": "sha256",
        "role": "admin|student",
        "full_name": "string",
        "email": "string|null",
        "status": "active|disabled",
        "created_at": "ISO-8601",
        "last_login": "ISO-8601|null",
        "desktop_type": "admin|student",
        "available_apps": ["app_id"],
        "meta": {},
    }


def _ensure_schema_file():
    if not os.path.exists(SCHEMA_PATH):
        _save_json(SCHEMA_PATH, _default_account_schema())


def _ensure_default_accounts():
    accounts = _load_accounts()
    if accounts:
        return

    admin_account = {
        "id": f"admin-{uuid4().hex[:8]}",
        "username": "it.admin",
        "password_hash": _hash_password("admin123"),
        "role": "admin",
        "full_name": "IT Administrator",
        "email": "it@demo.se",
        "status": "active",
        "created_at": _now_iso(),
        "last_login": None,
        "desktop_type": "admin",
        "available_apps": DEFAULT_ADMIN_APPS,
        "meta": {},
    }

    student_account = {
        "id": f"student-{uuid4().hex[:8]}",
        "username": "elev.anvandare",
        "password_hash": _hash_password("demo123"),
        "role": "student",
        "full_name": "Elev Användare",
        "email": "elev@demo.se",
        "status": "active",
        "created_at": _now_iso(),
        "last_login": None,
        "desktop_type": "student",
        "available_apps": DEFAULT_STUDENT_APPS,
        "meta": {},
    }

    _save_account(admin_account)
    _save_account(student_account)


def _sanitize_user(account: dict):
    safe = dict(account)
    safe.pop("password_hash", None)
    return safe


def _apps_from_ids(app_ids: List[str]):
    registry = _ensure_app_registry()
    apps = []
    for app_id in app_ids:
        app = registry.get(app_id)
        if app:
            apps.append(app)
    return apps


def _require_admin():
    user = session.get("user")
    return user and user.get("role") == "admin"


@app.before_request
def bootstrap_accounts():
    _ensure_dirs()
    _ensure_schema_file()
    _ensure_default_accounts()
    _ensure_app_registry()


@app.route("/")
def index():
    login_path = os.path.join(FRONTEND_DIR, "login", "login.html")
    with open(login_path, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/auth/sverkan-login")
def sverkan_login():
    username = request.args.get("username", "").strip()
    password = request.args.get("password", "")
    mode = request.args.get("mode", "shell")

    account = _find_account(username)
    if not account:
        return _login_failed()

    if account.get("status") != "active":
        return _login_failed("Kontot är inaktiverat")

    if _hash_password(password) != account.get("password_hash"):
        return _login_failed()

    account["last_login"] = _now_iso()
    _save_account(account)

    session["user"] = {
        "id": account.get("id"),
        "username": account.get("username"),
        "name": account.get("full_name"),
        "role": account.get("role"),
        "email": account.get("email"),
    }
    session["desktop_type"] = account.get("desktop_type", "student")
    session["available_apps"] = account.get("available_apps", [])
    session["mode"] = mode
    session.permanent = True

    return redirect("/home/shell") if mode == "shell" else redirect("/home/app")


def _login_failed(message: Optional[str] = None):
    msg = message or "Fel Sverkan ID eller lösenord."
    return f"""
        <html>
        <head>
            <title>Login misslyckades</title>
            <style>
                body {{
                    font-family: system-ui;
                    background: #05070b;
                    color: #f5f7fb;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                }}
                .error-box {{
                    text-align: center;
                    padding: 40px;
                    border: 1px solid rgba(255, 95, 87, 0.5);
                    border-radius: 18px;
                    background: rgba(15, 20, 30, 0.9);
                }}
                h1 {{ color: #ff5f57; margin-bottom: 16px; }}
                p {{ margin-bottom: 24px; color: #a4afc4; }}
                a {{
                    color: #4ba3ff;
                    text-decoration: none;
                    padding: 10px 20px;
                    border: 1px solid #4ba3ff;
                    border-radius: 999px;
                    display: inline-block;
                }}
                a:hover {{ background: rgba(75, 163, 255, 0.1); }}
            </style>
        </head>
        <body>
            <div class="error-box">
                <h1>Inloggning misslyckades</h1>
                <p>{msg}</p>
                <a href="/">Tillbaka till inloggning</a>
            </div>
        </body>
        </html>
    """


@app.route("/auth/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/home/<mode>")
def home(mode: str):
    if "user" not in session:
        return redirect("/")

    role = session.get("desktop_type", "student")
    if role == "admin":
        admin_desktop = os.path.join(FRONTEND_DIR, "admin", "desktop.html")
        if os.path.exists(admin_desktop):
            with open(admin_desktop, "r", encoding="utf-8") as f:
                return f.read()
    elif role == "mcu":
        mcu_desktop = os.path.join(FRONTEND_DIR, "mcu", "desktop.html")
        if os.path.exists(mcu_desktop):
            with open(mcu_desktop, "r", encoding="utf-8") as f:
                return f.read()
    student_desktop = os.path.join(FRONTEND_DIR, "students", "desktop.html")
    with open(student_desktop, "r", encoding="utf-8") as f:
        return f.read()
# MCU API: Get/Set master address
import threading
MCU_CONFIG_PATH = os.path.join(PROJECT_ROOT, "server", "mcu_config.json")
_mcu_config_lock = threading.Lock()

def _load_mcu_config():
    # Always return the public server address as the master address
    return {"address": PUBLIC_SERVER_ADDRESS}

def _save_mcu_config(cfg):
    with _mcu_config_lock:
        with open(MCU_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

@app.route("/api/mcu/address", methods=["GET"])
def api_mcu_get_address():
    if session.get("desktop_type") != "mcu":
        return jsonify({"error": "Unauthorized"}), 403
    # Always return the hardcoded public address
    return jsonify({"address": PUBLIC_SERVER_ADDRESS})

@app.route("/api/mcu/address", methods=["POST"])
def api_mcu_set_address():
    if session.get("desktop_type") != "mcu":
        return jsonify({"error": "Unauthorized"}), 403
    # Ignore any posted address and always return the hardcoded public address
    return jsonify({"address": PUBLIC_SERVER_ADDRESS})


@app.route("/skola-app")
def skola_app():
    if "user" not in session:
        return redirect("/")

    skola_path = os.path.join(FRONTEND_DIR, "students", "desktop.html")
    skola_html = os.path.join(FRONTEND_DIR, "students", "skola_app.html")

    if os.path.exists(skola_html):
        with open(skola_html, "r", encoding="utf-8") as f:
            return f.read()

    if os.path.exists(skola_path):
        with open(skola_path, "r", encoding="utf-8") as f:
            return f.read()

    return "Skola app saknas", 404


@app.route("/admin")
def admin_panel():
    if "user" not in session:
        return redirect("/")
    if session.get("desktop_type") != "admin":
        return "Unauthorized", 403

    admin_page = os.path.join(FRONTEND_DIR, "admin", "admin.html")
    if os.path.exists(admin_page):
        with open(admin_page, "r", encoding="utf-8") as f:
            return f.read()

    return "Adminpanel saknas", 404


@app.route("/api/user")
def api_user():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    user = session.get("user")
    app_ids = session.get("available_apps", [])
    apps = _apps_from_ids(app_ids)

    return jsonify({
        "user": user,
        "desktop_type": session.get("desktop_type", "student"),
        "available_apps": apps,
    })


@app.route("/api/admin/users", methods=["GET", "POST"])
def admin_users():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    if request.method == "GET":
        accounts = [_sanitize_user(a) for a in _load_accounts().values()]
        return jsonify({"users": accounts})

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role", "student")
    full_name = data.get("full_name", "")
    email = data.get("email")

    if not username or not password or not full_name:
        return jsonify({"error": "username, password, full_name required"}), 400

    if role not in {"admin", "student"}:
        return jsonify({"error": "role must be admin or student"}), 400

    if _find_account(username):
        return jsonify({"error": "username already exists"}), 409

    new_account = {
        "id": f"{role}-{uuid4().hex[:8]}",
        "username": username,
        "password_hash": _hash_password(password),
        "role": role,
        "full_name": full_name,
        "email": email,
        "status": "active",
        "created_at": _now_iso(),
        "last_login": None,
        "desktop_type": role,
        "available_apps": DEFAULT_ADMIN_APPS if role == "admin" else DEFAULT_STUDENT_APPS,
        "meta": {},
    }

    _save_account(new_account)
    return jsonify({"success": True, "user": _sanitize_user(new_account)})


@app.route("/api/admin/users/<username>", methods=["PUT"])
def admin_update_user(username: str):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    account = _find_account(username)
    if not account:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    previous_role = account.get("role")

    if "full_name" in data:
        account["full_name"] = data["full_name"]
    if "email" in data:
        account["email"] = data["email"]
    if "status" in data and data["status"] in {"active", "disabled"}:
        account["status"] = data["status"]
    if "role" in data and data["role"] in {"admin", "student"}:
        account["role"] = data["role"]
        account["desktop_type"] = data["role"]
        account["available_apps"] = DEFAULT_ADMIN_APPS if data["role"] == "admin" else DEFAULT_STUDENT_APPS
    if "password" in data and data["password"]:
        account["password_hash"] = _hash_password(data["password"])

    _save_account(account, previous_role=previous_role)
    return jsonify({"success": True, "user": _sanitize_user(account)})


@app.route("/api/admin/users/<username>/apps", methods=["PUT"])
def admin_update_user_apps(username: str):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    account = _find_account(username)
    if not account:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    apps = data.get("apps") or []

    if not isinstance(apps, list):
        return jsonify({"error": "apps must be a list"}), 400

    # Filter to known app IDs only
    registry = _ensure_app_registry()
    valid_ids = [app_id for app_id in apps if app_id in registry]
    account["available_apps"] = valid_ids

    _save_account(account, previous_role=account.get("role"))
    return jsonify({"success": True, "user": _sanitize_user(account)})


@app.route("/api/admin/apps")
def admin_apps():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    registry = _ensure_app_registry()
    return jsonify({"apps": list(registry.values())})


@app.route("/api/admin/apps", methods=["POST"])
def admin_add_app():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    app_name = (data.get("app_name") or "").strip()
    app_path = (data.get("app_path") or "").strip()
    app_icon = (data.get("app_icon") or "📦").strip()
    app_color = (data.get("app_color") or "#4ba3ff").strip()
    app_id = (data.get("app_id") or "").strip() or _slugify(app_name)

    if not app_name:
        return jsonify({"error": "app_name is required"}), 400

    registry = _ensure_app_registry()

    if app_id in registry:
        return jsonify({"error": "app_id already exists"}), 409

    new_app = {
        "app_id": app_id,
        "app_name": app_name,
        "app_icon": app_icon,
        "app_path": app_path or None,
        "app_color": app_color,
    }

    registry[app_id] = new_app
    _save_app_registry(registry)

    return jsonify({"success": True, "app": new_app})


@app.route("/api/admin/apps/refresh", methods=["POST"])
def admin_refresh_apps():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    registry = _ensure_app_registry()
    detected = _detect_office_apps()
    updated = False
    for app_id, app in detected.items():
        if app_id not in registry:
            registry[app_id] = app
            updated = True

    if updated:
        _save_app_registry(registry)

    return jsonify({"success": True, "apps": list(registry.values())})


@app.route("/api/admin/apps/<app_id>", methods=["DELETE"])
def admin_delete_app(app_id: str):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    registry = _ensure_app_registry()
    if app_id not in registry:
        return jsonify({"error": "App not found"}), 404

    registry.pop(app_id)
    _save_app_registry(registry)

    # Remove app from all accounts
    for path in _list_account_files():
        try:
            account = _load_json(path)
        except Exception:
            continue

        apps = account.get("available_apps") or []
        if app_id in apps:
            account["available_apps"] = [a for a in apps if a != app_id]
            _save_json(path, account)

    return jsonify({"success": True, "apps": list(registry.values())})


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": "sverkan-backend"})


@app.route("/api/launch-app", methods=["POST"])
def launch_app():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or {}
    app_id = data.get("app_id")
    force_new = bool(data.get("force_new"))
    if not app_id:
        return jsonify({"error": "app_id is required"}), 400

    allowed = session.get("available_apps", [])
    if app_id not in allowed:
        return jsonify({"error": "App not allowed"}), 403

    registry = _ensure_app_registry()
    app = registry.get(app_id)
    if not app:
        return jsonify({"error": "App not found"}), 404

    app_path = app.get("app_path")
    if not app_path or app_path.startswith("/") or app_path.startswith("http"):
        return jsonify({"error": "App has no launchable path"}), 400

    if not os.path.exists(app_path):
        return jsonify({"error": "App path not found"}), 404

    process = RUNNING_APPS.get(app_id)
    if process and process.poll() is None and not force_new:
        _bring_process_to_front(process.pid)
        return jsonify({"success": True, "already_running": True})

    try:
        process = subprocess.Popen([app_path])
        RUNNING_APPS[app_id] = process
    except Exception as e:
        return jsonify({"error": f"Launch failed: {e}"}), 500

    return jsonify({"success": True, "already_running": False})


@app.route("/api/activate-app", methods=["POST"])
def activate_app():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or {}
    app_id = data.get("app_id")
    if not app_id:
        return jsonify({"error": "app_id is required"}), 400

    process = RUNNING_APPS.get(app_id)
    if not process or process.poll() is not None:
        return jsonify({"error": "App not running"}), 404

    _bring_process_to_front(process.pid)
    return jsonify({"success": True})


@app.route("/api/close-app", methods=["POST"])
def close_app():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or {}
    app_id = data.get("app_id")
    if not app_id:
        return jsonify({"error": "app_id is required"}), 400

    process = RUNNING_APPS.get(app_id)
    if not process or process.poll() is not None:
        return jsonify({"success": True, "already_closed": True})

    try:
        if not _close_process_window(process.pid):
            process.terminate()
    except Exception as e:
        return jsonify({"error": f"Close failed: {e}"}), 500

    return jsonify({"success": True, "already_closed": False})


@app.route("/api/apps/status", methods=["POST"])
def apps_status():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or {}
    app_ids = data.get("app_ids") or []
    if not isinstance(app_ids, list):
        return jsonify({"error": "app_ids must be a list"}), 400

    status = {}
    for app_id in app_ids:
        process = RUNNING_APPS.get(app_id)
        status[app_id] = bool(process and process.poll() is None)

    return jsonify({"status": status})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=APP_PORT, debug=os.getenv("APP_ENV") == "development")
