import re

with open("radar_loop.py", "r") as f:
    code = f.read()

# Replace hardcoded values with os.getenv
env_setup = """import os
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
SCRAPER_API_KEYS = [k.strip() for k in os.getenv("SCRAPER_API_KEYS", "").split(",") if k.strip()]
"""

# Replace the block of imports and hardcoded vars
pattern = r"import os.*?SCRAPER_API_KEYS = \[\n.*?\]"
code = re.sub(pattern, env_setup, code, flags=re.DOTALL)

# Let's add the imports back since we deleted them
imports = """import os
import json
import time
import asyncio
import threading
import requests
import telebot
from telebot import types
from dotenv import load_dotenv
load_dotenv()
from scrapers.dubizzle import DubizzleScraper

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
SCRAPER_API_KEYS = [k.strip() for k in os.getenv("SCRAPER_API_KEYS", "").split(",") if k.strip()]"""

code = re.sub(r"import os.*?SCRAPER_API_KEYS = \[.*?\]\n?", imports + "\n", code, flags=re.DOTALL)

with open("radar_loop.py", "w") as f:
    f.write(code)

