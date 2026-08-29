import requests
import urllib.parse
from typing import List
from scrapers.base import BaseScraper
from models.result import SearchResult

class GoogleScraper(BaseScraper):
    def __init__(self, api_key: str):
        self.api_key = api_key
        super().__init__(None)

    async def search(self, query: str, time_filter: str = "") -> List[SearchResult]:
        results = []
        try:
            google_url = 'https://www.google.com/search?q=' + urllib.parse.quote(query)
            if time_filter:
                google_url += f"&tbs={time_filter}"
            
            api_url = f'http://api.scraperapi.com?api_key={self.api_key}&url={google_url}&autoparse=true&device_type=desktop'
            
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                organic_results = data.get('organic_results', [])
                
                for item in organic_results:
                    title = item.get('title')
                    link = item.get('link')
                    snippet = item.get('snippet')
                    
                    if title and link:
                        results.append(SearchResult(
                            source='Google Search',
                            title=title,
                            url=link,
                            description=snippet
                        ))
            else:
                print(f"ScraperAPI returned status code: {response.status_code}")
        except Exception as e:
            print(f'Failed to search Google via ScraperAPI: {e}')
            
        return results
