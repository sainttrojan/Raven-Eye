import re

with open("radar_loop.py", "r") as f:
    code = f.read()

# Add import
import_stmt = "from core.config import load_api_keys\n"
code = code.replace("from scrapers.dubizzle import DubizzleScraper", "from scrapers.dubizzle import DubizzleScraper\n" + import_stmt)

# Remove static SCRAPER_API_KEYS
code = re.sub(r"SCRAPER_API_KEYS = \[.*?\]\n", "", code, flags=re.DOTALL)

# Replace all occurrences of SCRAPER_API_KEYS with load_api_keys()
code = code.replace("SCRAPER_API_KEYS", "load_api_keys()")

with open("radar_loop.py", "w") as f:
    f.write(code)

