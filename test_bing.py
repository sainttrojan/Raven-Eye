import requests
from bs4 import BeautifulSoup
import urllib.parse

api_key = "efda9176f26841a181772cf1f7d5602c"
query = urllib.parse.quote("site:dubizzle.com.eg madinaty")
bing_url = f"https://www.bing.com/search?q={query}"
api_url = f"http://api.scraperapi.com?api_key={api_key}&url={bing_url}"

resp = requests.get(api_url)
soup = BeautifulSoup(resp.text, 'html.parser')
for li in soup.find_all('li', class_='b_algo'):
    h2 = li.find('h2')
    if not h2: continue
    a = h2.find('a')
    if not a: continue
    title = a.text
    link = a['href']
    p = li.find('p')
    snippet = p.text if p else ""
    print(f"[{title}]({link})\n{snippet}\n")
