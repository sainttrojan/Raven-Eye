import requests
from bs4 import BeautifulSoup
import urllib.parse
from typing import List
from scrapers.base import BaseScraper
from scrapers.google import GoogleScraper
from models.result import SearchResult
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

ZENROWS_BASE = "https://api.zenrows.com/v1/"

class DubizzleScraper(BaseScraper):
    def __init__(self, api_keys: List[str]):
        # api_keys kept for backward compat, we use ZenRows now
        self.api_keys = api_keys if isinstance(api_keys, list) else [api_keys]
        self.current_key_idx = 0
        super().__init__(None)

    def _get_zenrows_key(self) -> str:
        from core.config import load_zenrows_key
        return load_zenrows_key()

    def fetch_page(self, page: int, encoded_query: str) -> List[SearchResult]:
        results = []
        dubizzle_url = f"https://www.dubizzle.com.eg/properties/q-{encoded_query}/?page={page}"
        zenrows_key = self._get_zenrows_key()

        params = {
            "url": dubizzle_url,
            "apikey": zenrows_key,
            "js_render": "true",
            "wait": "2000",
            "premium_proxy": "true",
            "proxy_country": "eg",
        }

        print(f"DubizzleScraper [ZenRows]: Fetching page {page} → {dubizzle_url}")
        try:
            response = requests.get(ZENROWS_BASE, params=params, timeout=60)
            if response.status_code != 200:
                print(f"ZenRows error {response.status_code}: {response.text[:200]}")
                return results
            response_text = response.text
        except Exception as e:
            print(f"ZenRows request failed for page {page}: {e}")
            return results

        soup = BeautifulSoup(response_text, 'html.parser')

        # Try listings by aria-label first (most reliable)
        listings = soup.find_all('li', attrs={"aria-label": "Listing"})
        if not listings:
            # Fallback: find all ad links
            ad_links = soup.find_all('a', href=lambda href: href and '/ad/' in href)
            seen_urls = set()
            for link_tag in ad_links:
                url = link_tag['href']
                if not url.startswith('http'):
                    url = "https://www.dubizzle.com.eg" + url
                if url in seen_urls: continue
                seen_urls.add(url)
                item = link_tag.find_parent('li') or link_tag.find_parent('div')
                title = item.get('aria-label', link_tag.get('title', 'Unknown')) if item else 'Unknown'
                spans = item.find_all('span') if item else link_tag.find_all('span')
                texts = [s.text.strip() for s in spans if s.text.strip()]
                price = next((t for t in texts if 'ج.م' in t or 'EGP' in t), None)
                area  = next((t for t in texts if 'متر' in t or 'م٢' in t or 'sqm' in t), None)
                desc  = " - ".join(list(dict.fromkeys(texts[:10])))
                results.append(SearchResult(
                    source='Dubizzle', title=title, url=url,
                    description=desc, price=price, area=area, phone_number=None
                ))
            return results

        seen_urls = set()
        for li in listings:
            link_tag = li.find('a', href=lambda href: href and ('/ad/' in href or '/properties/' in href))
            if not link_tag:
                continue
            url = link_tag['href']
            if not url.startswith('http'):
                url = "https://www.dubizzle.com.eg" + url
            if url in seen_urls: continue
            seen_urls.add(url)

            # Extract real title — try heading first, then link title attr, then fallback
            title_el = li.find(['h2', 'h3', 'h4'])
            if title_el:
                title = title_el.text.strip()
            elif link_tag.get('title'):
                title = link_tag['title'].strip()
            else:
                # Find largest text block in the li
                all_divs = li.find_all('div')
                title = next((d.text.strip() for d in all_divs if len(d.text.strip()) > 10 and d.text.strip() not in ['', '\n']), 'Unknown')

            spans = li.find_all('span')
            texts = [s.text.strip() for s in spans if s.text.strip()]
            price = next((t for t in texts if 'ج.م' in t or 'EGP' in t), None)
            area  = next((t for t in texts if 'متر' in t or 'م٢' in t or 'sqm' in t), None)
            desc  = " - ".join(list(dict.fromkeys(texts[:10])))

            results.append(SearchResult(
                source='Dubizzle', title=title, url=url,
                description=desc, price=price, area=area, phone_number=None
            ))

        return results

    async def search(self, query: str, time_filter: str = "", max_pages: int = 5) -> List[SearchResult]:
        clean_query = re.sub(r'site:\S+', '', query).strip().replace(' ', '-')
        encoded_query = urllib.parse.quote(clean_query)

        all_results = []
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=5) as executor:
            tasks = [
                loop.run_in_executor(executor, self.fetch_page, page, encoded_query)
                for page in range(1, max_pages + 1)
            ]
            for completed_task in await asyncio.gather(*tasks):
                all_results.extend(completed_task)

        # Google fallback (uses ZenRows too, via GoogleScraper)
        if not all_results:
            print("Dubizzle ZenRows scrape returned nothing. Falling back to GoogleScraper...")
            fallback_scraper = GoogleScraper(self.api_keys)
            fallback_query = f"{query} site:dubizzle.com.eg inurl:ad"
            return await fallback_scraper.search(fallback_query, time_filter, max_pages=max_pages)

        return all_results
