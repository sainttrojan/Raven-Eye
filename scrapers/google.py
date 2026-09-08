import requests
import urllib.parse
from typing import List
from scrapers.base import BaseScraper
from models.result import SearchResult
from core.parser import SmartParser
import re

class GoogleScraper(BaseScraper):
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys if isinstance(api_keys, list) else [api_keys]
        self.current_key_idx = 0
        super().__init__(None)


    def resolve_google_url(self, url: str) -> str:
        if 'google.com/goto?url=' in url or 'google.com/url?q=' in url:
            try:
                resp = requests.get(url, allow_redirects=False, timeout=10)
                if resp.status_code in [301, 302]:
                    return resp.headers.get('Location', url)
            except Exception:
                pass
        return url

    def is_valid_listing(self, url: str) -> bool:
        """Filters out category and search pages to ensure we get individual listings."""
        url_lower = url.lower()
        
        # 1. Global Exclusions (Any site)
        invalid_patterns = [
            r'/search', r'\?search=', r'/category/', r'/find', r'page=', 
            r'/agent/', r'/broker/', r'/company/', r'/directory/', r'/users/',
            r'/properties/rent', r'/properties/sale', r'/properties/for-',
            r'dubizzle.com.eg/properties/?$', r'propertyfinder.eg/en/?$'
        ]
        for pattern in invalid_patterns:
            if re.search(pattern, url_lower):
                return False

        # 2. Site-Specific Enforcements
        # Dubizzle (Must contain /ad/ or /item/ or ID at the end)
        if 'dubizzle.com' in url_lower:
            if not re.search(r'(/ad/|-id\d+\.html|/item/)', url_lower):
                return False
                
        # Property Finder (Must end in .html or contain /placements/)
        elif 'propertyfinder.' in url_lower:
            if not (url_lower.endswith('.html') or '/placements/' in url_lower):
                return False
                
        # Aqarmap (Must contain /listing/ or /project/)
        elif 'aqarmap.' in url_lower:
            if not re.search(r'(/listing/|/project/)', url_lower):
                return False
                
        # Facebook (Exclude pages/groups main page, must be a post)
        elif 'facebook.com' in url_lower:
            if not re.search(r'(/posts/|/permalink/|/videos/|/photos/|fbid=)', url_lower):
                return False
                
        # Twitter / X (Must contain /status/)
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            if '/status/' not in url_lower:
                return False
                
        # Instagram (Must contain /p/ or /reel/)
        elif 'instagram.com' in url_lower:
            if not re.search(r'(/p/|/reel/)', url_lower):
                return False

        return True

    async def search(self, query: str, time_filter: str = "", max_pages: int = 5) -> List[SearchResult]:
        results = []
        try:
            for page in range(max_pages):
                start_index = page * 10
                google_url = f'https://www.google.com/search?q={urllib.parse.quote(query)}&start={start_index}'
                if time_filter:
                    google_url += f"&tbs={time_filter}"
                
                # Retry loop for API keys
                success = False
                for _ in range(len(self.api_keys)):
                    current_api_key = self.api_keys[self.current_key_idx]
                    api_url = f'http://api.scraperapi.com?api_key={current_api_key}&url={google_url}&autoparse=true&device_type=desktop'
                    
                    print(f"Fetching page {page + 1} using API Key ending in ...{current_api_key[-4:] if current_api_key else ''}")
                    try:
                        response = requests.get(api_url, timeout=60)
                        if response.status_code == 200:
                            success = True
                            data = response.json()
                            organic_results = data.get('organic_results', [])
                            break
                        elif response.status_code in [403, 401, 429]:
                            print(f"API Key ...{current_api_key[-4:]} failed with {response.status_code}. Rotating key...")
                            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
                        else:
                            print(f"ScraperAPI returned status code: {response.status_code}")
                            break # Other error, just break out of rotation
                    except Exception as e:
                        print(f"Request failed: {e}. Rotating key...")
                        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
                
                if not success:
                    print("All API keys failed or max pages reached.")
                    break
                    
                if not organic_results:
                    break
                    
                for item in organic_results:
                        title = item.get('title')
                        link = item.get('link')
                        snippet = item.get('snippet')
                        
                        if title and link:
                            if not self.is_valid_listing(link):
                                continue
                                
                            full_text = f"{title} {snippet}"
                            parsed_data = SmartParser.parse_text(full_text)
                            
                            results.append(SearchResult(
                                source='Google Search',
                                title=title,
                                url=link,
                                description=snippet,
                                price=parsed_data.get('price'),
                                area=parsed_data.get('area'),
                                phone_number=parsed_data.get('phone_number')
                            ))
                else:
                    print(f"ScraperAPI returned status code: {response.status_code}")
                    break
        except Exception as e:
            print(f'Failed to search Google via ScraperAPI: {e}')
            
        return results
