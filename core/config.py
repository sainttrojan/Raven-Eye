import json
import os
from dotenv import load_dotenv

load_dotenv()
CONFIG_FILE = "config.json"

def load_api_keys():
    """Load ScraperAPI keys (kept for web-footprint Google search only)."""
    keys = []
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                keys = data.get("api_keys", [])
        except: pass

    if not keys:
        env_keys = os.getenv("SCRAPER_API_KEYS", "")
        keys = [k.strip() for k in env_keys.split(",") if k.strip()]

    if not keys:
        keys = [
            "085a9eef6828dfd6bb77a6f30ca19b3b",
            "af5da6333540757495114e2c35cf685d",
            "df094a68b9768ecf6a694cd4ab045fdb",
            "15428b0bc961dc879128ca2e8db2ab61",
            "efda9176f26841a181772cf1f7d5602c"
        ]
    return keys

def load_zenrows_key() -> str:
    """Return the active ZenRows API key (primary scraping engine)."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                key = data.get("zenrows_key", "")
                if key:
                    return key
        except: pass
    env_key = os.getenv("ZENROWS_API_KEY", "")
    if env_key:
        return env_key
    return "e3565d1d68bca965d2b4808d1d8413ec04bf2aea"

def save_api_keys(keys):
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        except: pass
    data["api_keys"] = keys
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f)

def save_zenrows_key(key: str):
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        except: pass
    data["zenrows_key"] = key
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f)

def load_database_url() -> str:
    """Supabase Postgres URL (empty = local SQLite)."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                url = json.load(f).get("database_url", "")
                if url:
                    return url
        except: pass
    return os.getenv("DATABASE_URL", "")

def save_database_url(url: str):
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        except: pass
    data["database_url"] = url.strip()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f)

def load_sheet_id() -> str:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                sid = json.load(f).get("sheet_id", "")
                if sid:
                    return sid
        except: pass
    return os.getenv("SHEET_ID", "")

def save_sheet_id(sheet_id: str):
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        except: pass
    data["sheet_id"] = sheet_id.strip()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f)

def load_google_creds() -> str:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                path = json.load(f).get("google_creds", "")
                if path:
                    return os.path.expanduser(os.path.expandvars(path))
        except: pass
    return os.path.expanduser(os.path.expandvars(
        os.getenv("GOOGLE_CREDENTIALS_FILE", "")))

def save_google_creds(path: str):
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        except: pass
    data["google_creds"] = path.strip()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f)

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
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                groups = json.load(f).get("fb_groups", [])
                if groups:
                    return [g.strip() for g in groups if g.strip()]
        except: pass
    env_groups = os.getenv("FB_GROUPS", "")
    if env_groups:
        return [g.strip() for g in env_groups.replace(",", "\n").split("\n") if g.strip()]
    return []

def save_fb_groups(groups):
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        except: pass
    data["fb_groups"] = [g.strip() for g in groups if g.strip()]
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f)
