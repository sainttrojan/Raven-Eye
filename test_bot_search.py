import asyncio
from scrapers.google import GoogleScraper
from core.config import load_api_keys

def test_search():
    query = "شقة للبيع مدينتي"
    site_option = "جميع المواقع"
    time_option = "أي وقت"
    exact_match = False
    
    final_query = query
    time_filter = ""
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def fetch():
        scraper = GoogleScraper(load_api_keys())
        return await scraper.search(final_query, time_filter, max_pages=1)
            
    results = loop.run_until_complete(fetch())
    print("Found:", len(results))
    for r in results:
        print(r.title)

test_search()
