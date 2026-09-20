with open("app.py", "r") as f:
    content = f.read()

# Add import
if "from scrapers.dubizzle import DubizzleScraper" not in content:
    content = content.replace("from scrapers.google import GoogleScraper", "from scrapers.google import GoogleScraper\nfrom scrapers.dubizzle import DubizzleScraper")

# Modify fetch_results
old_fetch = """        async def fetch_results():
            google_scraper = GoogleScraper(st.session_state['api_keys'])
            return await google_scraper.search(final_query, time_filter, max_pages=max_pages)"""

new_fetch = """        async def fetch_results():
            if site_option == "Dubizzle فقط":
                scraper = DubizzleScraper(st.session_state['api_keys'])
                return await scraper.search(query, time_filter, max_pages=max_pages)
            else:
                scraper = GoogleScraper(st.session_state['api_keys'])
                return await scraper.search(final_query, time_filter, max_pages=max_pages)"""

content = content.replace(old_fetch, new_fetch)

with open("app.py", "w") as f:
    f.write(content)
