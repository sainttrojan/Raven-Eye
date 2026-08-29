import asyncio
import pandas as pd
from scrapers.google import GoogleScraper

async def main():
    search_query = "شقة ايجار بمدينتي من المالك"
    print(f"Starting scraping for query: '{search_query}'\n")

    all_results = []
    
    print("--- Scraping Google (Latest Results) ---")
    scraper_api_key = "06ede5861ed79f12ad4ed6f275ce0038"
    google_scraper = GoogleScraper(scraper_api_key)
    google_results = await google_scraper.search(search_query)
    print(f"Found {len(google_results)} results on Google.")
    all_results.extend(google_results)
    
    # 2. Facebook Scraping Disabled Temporarily
    
    if all_results:
        print("\n--- Saving Results ---")
        data = []
        for result in all_results:
            data.append({
                'المصدر': result.source,          
                'العنوان': result.title,           
                'الرابط': result.url,             
                'الوصف': result.description      
            })
            
        df = pd.DataFrame(data)
        output_file = 'results.xlsx'
        df.to_excel(output_file, index=False)
        print(f"Saved {len(all_results)} results to {output_file}")
    else:
        print("No results found.")

if __name__ == "__main__":
    asyncio.run(main())
