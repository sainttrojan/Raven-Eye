import asyncio
import pandas as pd
from scrapers.google import GoogleScraper
from core.db import DatabaseManager

async def main():
    search_query = "شقة ايجار بمدينتي من المالك"
    print(f"Starting scraping for query: '{search_query}'\n")

    all_results = []
    
    print("--- Scraping Google (Latest Results) ---")
    scraper_api_key = "06ede5861ed79f12ad4ed6f275ce0038"
    google_scraper = GoogleScraper(scraper_api_key)
    google_results = await google_scraper.search(search_query, max_pages=10)
    print(f"Found {len(google_results)} results on Google.")
    all_results.extend(google_results)
    
    db = DatabaseManager()
    
    if all_results:
        print("\n--- Saving Results ---")
        data = []
        new_count = 0
        for result in all_results:
            res_dict = result.to_dict()
            data.append({
                'المصدر': res_dict['Source'],          
                'العنوان': res_dict['Title'],           
                'السعر': res_dict.get('Price', ''),           
                'المساحة': res_dict.get('Area', ''),           
                'رقم الهاتف': res_dict.get('Phone Number', ''),           
                'الرابط': res_dict['URL'],             
                'الوصف': res_dict['Description']      
            })
            if db.insert_property(res_dict):
                new_count += 1
            
        df = pd.DataFrame(data)
        output_file = 'results.xlsx'
        df.to_excel(output_file, index=False)
        print(f"Saved {len(all_results)} results to {output_file}")
        print(f"Inserted {new_count} new unique properties to database.")
    else:
        print("No results found.")

if __name__ == "__main__":
    asyncio.run(main())
