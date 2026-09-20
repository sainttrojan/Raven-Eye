import requests
import json

api_url = "http://api.scraperapi.com?api_key=efda9176f26841a181772cf1f7d5602c&url=https://www.google.com.eg/search?q=site:dubizzle.com.eg/ad/+madinaty&autoparse=true"
resp = requests.get(api_url)
data = resp.json()
for r in data.get("organic_results", []):
    print("Title:", r.get("title"))
    print("Displayed:", r.get("displayed_link"))
    print("---")
