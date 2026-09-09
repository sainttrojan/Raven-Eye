import requests
from bs4 import BeautifulSoup
import urllib.parse
from typing import List
from scrapers.base import BaseScraper
from models.result import SearchResult
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

class DubizzleScraper(BaseScraper):
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys if isinstance(api_keys, list) else [api_keys]
        self.current_key_idx = 0
        super().__init__(None)

    def fetch_page(self, page: int, encoded_query: str) -> List[SearchResult]:
        results = []
        dubizzle_url = f"https://www.dubizzle.com.eg/properties/q-{encoded_query}/?page={page}"
        
        success = False
        response_text = ""
        for _ in range(len(self.api_keys)):
            current_api_key = self.api_keys[self.current_key_idx]
            api_url = f'http://api.scraperapi.com?api_key={current_api_key}&url={dubizzle_url}&render=true'
            
            print(f"DubizzleScraper: Fetching page {page} using API Key ending in ...{current_api_key[-4:] if current_api_key else ''}")
            try:
                response = requests.get(api_url, timeout=60)
                if response.status_code == 200:
                    success = True
                    response_text = response.text
                    break
                elif response.status_code in [403, 401, 429]:
                    print(f"API Key ...{current_api_key[-4:]} failed with {response.status_code}. Rotating key...")
                    self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
                else:
                    print(f"ScraperAPI returned status code: {response.status_code} for page {page}")
                    break
            except Exception as e:
                print(f"Request failed for page {page}: {e}. Rotating key...")
                self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        
        if not success:
            print(f"Failed to fetch page {page}")
            return results
            
        soup = BeautifulSoup(response_text, 'html.parser')
        ad_links = soup.find_all('a', href=lambda href: href and '/ad/' in href)
        
        if not ad_links:
            print(f"No ad links found on page {page}.")
            return results
            
        seen_urls = set()
        
        for link_tag in ad_links:
            url = link_tag['href']
            if not url.startswith('http'):
                url = "https://www.dubizzle.com.eg" + url
                
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            item = link_tag.find_parent('li')
            if not item:
                item = link_tag.find_parent('div')
                
            title = item.get('aria-label', link_tag.get('title', 'Unknown')) if item else 'Unknown'
            if title == 'Unknown' or not title:
                title_elem = link_tag.find('div', string=True)
                if title_elem: title = title_elem.text
                
            spans = item.find_all('span') if item else link_tag.find_all('span')
            texts = [s.text.strip() for s in spans if s.text.strip()]
            
            price = next((t for t in texts if 'ج.م' in t or 'EGP' in t), None)
            area = next((t for t in texts if 'متر' in t or 'م٢' in t or 'sqm' in t), None)
            
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

    async def search(self, query: str, time_filter: str = "", max_pages: int = 5) -> List[SearchResult]:
        clean_query = re.sub(r'site:\S+', '', query).strip().replace(' ', '-')
        encoded_query = urllib.parse.quote(clean_query)
        
        all_results = []
        loop = asyncio.get_event_loop()
        
        # We use a ThreadPoolExecutor with max_workers=5 to respect ScraperAPI's 5 concurrent threads limit on free plans
        with ThreadPoolExecutor(max_workers=5) as executor:
            tasks = [
                loop.run_in_executor(executor, self.fetch_page, page, encoded_query)
                for page in range(1, max_pages + 1)
            ]
            
            for completed_task in await asyncio.gather(*tasks):
                all_results.extend(completed_task)
                
        return all_results
