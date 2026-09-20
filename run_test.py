import asyncio
from scrapers.dubizzle import DubizzleScraper

async def main():
    scraper = DubizzleScraper(['efda9176f26841a181772cf1f7d5602c'])
    results = await scraper.search('شقة للبيع مدينتي', max_pages=1)
    if not results:
        print("0 results returned.")
    else:
        print(f"Found {len(results)} results!")
    for r in results[:3]:
        print(f"[{r.title}]({r.url})")
        print(f"Price: {r.price} | Area: {r.area}")
        print(f"Desc: {r.description}\n")

if __name__ == "__main__":
    asyncio.run(main())
