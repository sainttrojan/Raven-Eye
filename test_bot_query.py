import asyncio
from scrapers.google import GoogleScraper
from core.config import load_api_keys

def test_search():
    query = "شقة للبيع في مدينتي"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def fetch():
        scraper = GoogleScraper(load_api_keys())
        return await scraper.search(query, "", max_pages=3)
            
    results = loop.run_until_complete(fetch())
    print("Found:", len(results))

test_search()
