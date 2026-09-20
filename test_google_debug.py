import requests
import urllib.parse
api_key = "085a9eef6828dfd6bb77a6f30ca19b3b"
google_url = f'https://www.google.com/search?q={urllib.parse.quote("شقة للبيع مدينتي site:dubizzle.com.eg inurl:ad")}&start=0'
api_url = f'http://api.scraperapi.com?api_key={api_key}&url={google_url}&autoparse=true&device_type=desktop'

resp = requests.get(api_url)
print(resp.status_code)
data = resp.json()
print("Organic results:", len(data.get('organic_results', [])))
for item in data.get('organic_results', [])[:3]:
    print(item.get('title'))
    print(item.get('link'))
