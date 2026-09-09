import requests
from bs4 import BeautifulSoup
import urllib.parse
from typing import List
from scrapers.base import BaseScraper
from models.result import SearchResult
import re

class DubizzleScraper(BaseScraper):
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys if isinstance(api_keys, list) else [api_keys]
        self.current_key_idx = 0
        super().__init__(None)

    async def search(self, query: str, time_filter: str = "", max_pages: int = 5) -> List[SearchResult]:
        results = []
        
        # Remove google dork strings from query
        clean_query = re.sub(r'site:\S+', '', query).strip()
        
        for page in range(1, max_pages + 1):
            encoded_query = urllib.parse.quote(clean_query)
            dubizzle_url = f"https://www.dubizzle.com.eg/properties/q-{encoded_query}/?page={page}"
            
            success = False
            for _ in range(len(self.api_keys)):
                current_api_key = self.api_keys[self.current_key_idx]
                api_url = f'http://api.scraperapi.com?api_key={current_api_key}&url={dubizzle_url}&render=true'
                
                print(f"DubizzleScraper: Fetching page {page} using API Key ending in ...{current_api_key[-4:] if current_api_key else ''}")
                try:
                    response = requests.get(api_url, timeout=30)
                    if response.status_code == 200:
                        success = True
                        break
                    elif response.status_code in [403, 401, 429]:
                        print(f"API Key ...{current_api_key[-4:]} failed with {response.status_code}. Rotating key...")
                        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
                    else:
                        print(f"ScraperAPI returned status code: {response.status_code}")
                        break
                except Exception as e:
                    print(f"Request failed: {e}. Rotating key...")
                    self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            
            if not success:
                print("All API keys failed or max pages reached.")
                break
                
            print(response.status_code, len(response.text)); soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('article')
            if not articles:
                print(f"No articles found on page {page}.")
                break
                
            for a in articles:
                link_tag = a.find('a', href=True)
                if not link_tag: continue
                
                url = link_tag['href']
                if not url.startswith('http'):
                    url = "https://www.dubizzle.com.eg" + url
                    
                title = a.get('aria-label', link_tag.get('title', 'Unknown'))
                if title == 'Unknown' or not title:
                    title_elem = link_tag.find('div', string=True)
                    if title_elem: title = title_elem.text
                    
                spans = a.find_all('span')
                texts = [s.text.strip() for s in spans if s.text.strip()]
                
                price = next((t for t in texts if 'ج.م' in t or 'EGP' in t), None)
                area = next((t for t in texts if 'متر' in t or 'م٢' in t or 'sqm' in t), None)
                
                # Remove duplicate words in description
                desc = " - ".join(list(dict.fromkeys(texts[:10])))
                
                results.append(SearchResult(
                    source='Dubizzle',
                    title=title,
                    url=url,
                    description=desc,
                    price=price,
                    area=area,
                    phone_number=None
                ))
                
        return results
