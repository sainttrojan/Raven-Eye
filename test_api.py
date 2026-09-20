import asyncio
from scrapers.google import GoogleScraper

async def main():
    scraper = GoogleScraper(["d868af7919cadbcc269fef0bfecff8e6"])
    results = await scraper.search("site:dubizzle.com.eg شقة للايجار بمدينتي", max_pages=1)
    if results:
        for r in results:
            print(r.url)
    else:
        print("No results found. URL filter might be too strict or API failed.")

asyncio.run(main())
