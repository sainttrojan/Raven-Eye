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
