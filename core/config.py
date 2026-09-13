import json
import os
from dotenv import load_dotenv

load_dotenv()
CONFIG_FILE = "config.json"

def load_api_keys():
    keys = []
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                keys = data.get("api_keys", [])
        except: pass
        
    if not keys:
        # Fallback to .env
        env_keys = os.getenv("SCRAPER_API_KEYS", "")
        keys = [k.strip() for k in env_keys.split(",") if k.strip()]
        
    if not keys:
        # Absolute default fallback
        keys = [
            "085a9eef6828dfd6bb77a6f30ca19b3b",
            "af5da6333540757495114e2c35cf685d",
            "df094a68b9768ecf6a694cd4ab045fdb",
            "15428b0bc961dc879128ca2e8db2ab61",
            "efda9176f26841a181772cf1f7d5602c"
        ]
        
    return keys

def save_api_keys(keys):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"api_keys": keys}, f)
