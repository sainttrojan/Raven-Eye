import json
import os
from dotenv import load_dotenv

load_dotenv()
CONFIG_FILE = "config.json"

try:
    from core.config_crypto import load_config_dict as _load_enc, save_config_dict as _save_enc, is_encrypted as _is_enc
except ImportError:
    _load_enc = _save_enc = None
    def _is_enc(): return False

def _load_dict() -> dict:
    if _load_enc and _is_enc():
        try:
            d = _load_enc()
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_dict(patch: dict):
    base = _load_dict()
    base.update(patch)
    if _save_enc and _is_enc():
        try:
            _save_enc(base)
            return
        except Exception:
            pass
    # Fallback: encrypted helper will switch to enc on next save if key appears
    if _save_enc:
        try:
            # If a key is available, prefer encrypted storage
            from core.config_crypto import _load_key
            if _load_key():
                _save_enc(base)
                return
        except Exception:
            pass
    with open(CONFIG_FILE, 'w') as f:
        json.dump(base, f, ensure_ascii=False, indent=2)

def load_api_keys():
    """Load ScraperAPI keys (kept for web-footprint Google search only)."""
    d = _load_dict()
    keys = d.get("api_keys", [])
    if keys:
        return keys
    env_keys = os.getenv("SCRAPER_API_KEYS", "")
    keys = [k.strip() for k in env_keys.split(",") if k.strip()]
    if keys:
        return keys
    return [
        "085a9eef6828dfd6bb77a6f30ca19b3b",
        "af5da6333540757495114e2c35cf685d",
        "df094a68b9768ecf6a694cd4ab045fdb",
        "15428b0bc961dc879128ca2e8db2ab61",
        "efda9176f26841a181772cf1f7d5602c"
    ]

def load_zenrows_key() -> str:
    """Return the active ZenRows API key (primary scraping engine)."""
    d = _load_dict()
    key = d.get("zenrows_key", "")
    if key:
        return key
    env_key = os.getenv("ZENROWS_API_KEY", "")
    if env_key:
        return env_key
    return "e3565d1d68bca965d2b4808d1d8413ec04bf2aea"

def save_api_keys(keys):
    _save_dict({"api_keys": keys})

def save_zenrows_key(key: str):
    _save_dict({"zenrows_key": key})

def load_database_url() -> str:
    """Supabase Postgres URL (empty = local SQLite)."""
    d = _load_dict()
    url = d.get("database_url", "")
    if url:
        return url
    return os.getenv("DATABASE_URL", "")

def save_database_url(url: str):
    _save_dict({"database_url": url.strip()})

def load_sheet_id() -> str:
    d = _load_dict()
    sid = d.get("sheet_id", "")
    if sid:
        return sid
    return os.getenv("SHEET_ID", "")

def save_sheet_id(sheet_id: str):
    _save_dict({"sheet_id": sheet_id.strip()})

def load_google_creds() -> str:
    d = _load_dict()
    path = d.get("google_creds", "")
    if path:
        return os.path.expanduser(os.path.expandvars(path))
    return os.path.expanduser(os.path.expandvars(
        os.getenv("GOOGLE_CREDENTIALS_FILE", "")))

def save_google_creds(path: str):
    _save_dict({"google_creds": path.strip()})

def load_admin_hash() -> str:
    """SHA256 of the admin password (empty = open access, no lock)."""
    d = _load_dict()
    h = d.get("admin_hash", "")
    if h:
        return h
    return os.getenv("RAVEN_ADMIN_HASH", "")

def save_admin_hash(hex_digest: str):
    _save_dict({"admin_hash": hex_digest.strip()})

# ---------- Facebook Marketplace session ----------
# One-time manual login via `venv/bin/python fb_login.py` saves the
# authenticated storage state here; scrapers reuse it afterwards.
FB_STORAGE_FILE = os.getenv("FB_STORAGE_FILE", "fb_storage_state.json")
FB_COOKIES_FILE = os.getenv("FB_COOKIES_FILE", "fb_cookies.json")

def fb_session_available() -> bool:
    """True if a saved Facebook session exists (storage state or cookies)."""
    return os.path.exists(FB_STORAGE_FILE) or os.path.exists(FB_COOKIES_FILE)

def load_fb_groups():
    """Group URLs/ids for Facebook Groups scraping (one per line in settings)."""
    d = _load_dict()
    groups = d.get("fb_groups", [])
    if groups:
        return [g.strip() for g in groups if g.strip()]
    env_groups = os.getenv("FB_GROUPS", "")
    if env_groups:
        return [g.strip() for g in env_groups.replace(",", "\n").split("\n") if g.strip()]
    return []

def save_fb_groups(groups):
    _save_dict({"fb_groups": [g.strip() for g in groups if g.strip()]})
