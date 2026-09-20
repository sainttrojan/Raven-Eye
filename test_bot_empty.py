import asyncio
from scrapers.google import GoogleScraper

keys = [
    "085a9eef6828dfd6bb77a6f30ca19b3b",
    "af5da6333540757495114e2c35cf685d",
    "df094a68b9768ecf6a694cd4ab045fdb",
    "15428b0bc961dc879128ca2e8db2ab61",
    "efda9176f26841a181772cf1f7d5602c"
]

def test_search():
    query = "شقة للبيع مدينتي"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def fetch():
        scraper = GoogleScraper(keys)
        return await scraper.search(query, "", max_pages=3)
            
    results = loop.run_until_complete(fetch())
    print("Found:", len(results))
    for r in results:
        print(r.title)

test_search()
