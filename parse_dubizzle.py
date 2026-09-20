import requests
from bs4 import BeautifulSoup
import json

url = "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/madinaty/"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

articles = soup.find_all('article')
for a in articles:
    link_tag = a.find('a', href=True)
    if not link_tag: continue
    
    url = "https://www.dubizzle.com.eg" + link_tag['href']
    title = a.get('aria-label', link_tag.get('title', 'Unknown'))
    
    print("URL:", url)
    print("Title:", title)
    
    # Let's find price
    spans = a.find_all('span')
    texts = [s.text.strip() for s in spans if s.text.strip()]
    print("Spans:", texts[:10])
    print("---")
    break
