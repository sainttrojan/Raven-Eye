import asyncio
from scrapers.dubizzle import DubizzleScraper
from core.config import load_api_keys

def test_search():
    query = "شقة للبيع مدينتي"
    time_filter = ""
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def fetch():
        scraper = DubizzleScraper(load_api_keys())
        return await scraper.search(query, time_filter, max_pages=1)
            
    results = loop.run_until_complete(fetch())
    print("Found:", len(results))

test_search()
