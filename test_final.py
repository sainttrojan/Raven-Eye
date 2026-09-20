import asyncio

# Test 1: ZenRows key loads
from core.config import load_zenrows_key
key = load_zenrows_key()
print(f"✅ ZenRows key: ...{key[-6:]}")

# Test 2: DubizzleScraper uses ZenRows
from scrapers.dubizzle import DubizzleScraper
s = DubizzleScraper([])
print(f"✅ DubizzleScraper instantiated, ZenRows key: ...{s._get_zenrows_key()[-6:]}")

# Test 3: Quick live scrape
import urllib.parse
q = urllib.parse.quote("شقة-للبيع-في-مدينتي-من-المالك")
res = s.fetch_page(1, q)
print(f"✅ Live scrape returned {len(res)} listings")
if res:
    print(f"   Sample: {res[0].title[:50]}")
