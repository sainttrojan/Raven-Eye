import requests
from bs4 import BeautifulSoup

ZENROWS_KEY = "e3565d1d68bca965d2b4808d1d8413ec04bf2aea"

url = "https://www.dubizzle.com.eg/properties/q-شقة-للبيع-في-مدينتي-من-المالك/?page=1"

params = {
    "url": url,
    "apikey": ZENROWS_KEY,
    "js_render": "true",          # Same as render=true in ScraperAPI
    "wait": "2000",               # Wait 2s for JS to load
    "premium_proxy": "true",      # Premium Egyptian proxy
    "proxy_country": "eg",        # Egypt proxy for local pricing
}

print("Testing ZenRows with Dubizzle...")
resp = requests.get("https://api.zenrows.com/v1/", params=params, timeout=60)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    soup = BeautifulSoup(resp.text, "html.parser")
    listings = soup.find_all("li", attrs={"aria-label": "Listing"})
    print(f"✅ SUCCESS! Found {len(listings)} listings")
    if listings:
        # Try to extract a title from first listing
        title_el = listings[0].find(attrs={"data-testid": True})
        print(f"First listing snippet: {listings[0].text[:100].strip()}")
else:
    print(f"❌ FAILED: {resp.status_code}")
    print(resp.text[:300])
