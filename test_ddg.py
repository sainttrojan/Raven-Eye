from duckduckgo_search import DDGS
import json
with DDGS() as ddgs:
    results = [r for r in ddgs.text("site:dubizzle.com.eg madinaty", max_results=30)]
for r in results:
    url = r['href']
    if 'dubizzle.com' in url and '/ad/' in url or '-id' in url:
        print(url)
