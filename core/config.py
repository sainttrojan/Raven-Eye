import json
import os

CONFIG_FILE = "config.json"

def load_api_keys():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return data.get("api_keys", [])
    return ["06ede5861ed79f12ad4ed6f275ce0038"] # Default

def save_api_keys(keys):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"api_keys": keys}, f)
