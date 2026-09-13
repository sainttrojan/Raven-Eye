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
        keys = ["06ede5861ed79f12ad4ed6f275ce0038"]
        
    return keys

def save_api_keys(keys):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"api_keys": keys}, f)
