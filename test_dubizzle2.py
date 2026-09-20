import asyncio
from scrapers.dubizzle import DubizzleScraper
import os

keys = [
    "085a9eef6828dfd6bb77a6f30ca19b3b",
    "af5da6333540757495114e2c35cf685d",
    "df094a68b9768ecf6a694cd4ab045fdb",
    "15428b0bc961dc879128ca2e8db2ab61",
    "efda9176f26841a181772cf1f7d5602c"
]

async def main():
    scraper = DubizzleScraper(keys)
    res = await scraper.search("شقة للبيع مدينتي", max_pages=1)
    for r in res:
        print(r.title)
        print(r.description)
        print("-----")
    print("Total:", len(res))

asyncio.run(main())
