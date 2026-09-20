from scrapers.google import GoogleScraper
scraper = GoogleScraper([])
url = "https://www.google.com/goto?url=CAES3QEB6zswFek3zkrZ98aIcO3hnBl4bL4JQckrl_x"
print("Valid:", scraper.is_valid_listing(url))
