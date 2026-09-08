import requests
import urllib.parse
from typing import List
from scrapers.base import BaseScraper
from models.result import SearchResult
from core.parser import SmartParser

class GoogleScraper(BaseScraper):
    def __init__(self, api_key: str):
        self.api_key = api_key
        super().__init__(None)

    async def search(self, query: str, time_filter: str = "", max_pages: int = 5) -> List[SearchResult]:
        results = []
        try:
            for page in range(max_pages):
                start_index = page * 10
                google_url = f'https://www.google.com/search?q={urllib.parse.quote(query)}&start={start_index}'
                if time_filter:
                    google_url += f"&tbs={time_filter}"
                
                api_url = f'http://api.scraperapi.com?api_key={self.api_key}&url={google_url}&autoparse=true&device_type=desktop'
                
                print(f"Fetching page {page + 1}...")
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    organic_results = data.get('organic_results', [])
                    
                    if not organic_results:
                        # No more results found
                        break
                        
                    for item in organic_results:
                        title = item.get('title')
                        link = item.get('link')
                        snippet = item.get('snippet')
                        
                        if title and link:
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
                    break  # Stop pagination on error
        except Exception as e:
            print(f'Failed to search Google via ScraperAPI: {e}')
            
        return results
