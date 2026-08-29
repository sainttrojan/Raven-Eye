import asyncio
from typing import List
from scrapers.base import BaseScraper
from models.result import SearchResult

class FacebookScraper(BaseScraper):
    async def search(self, query: str) -> List[SearchResult]:
        results = []
        try:
            # We assume the session is already logged in here
            # Go directly to marketplace search
            from urllib.parse import quote
            url = f"https://www.facebook.com/marketplace/search/?query={quote(query)}"
            await self.page.goto(url, wait_until='networkidle')
            
            # Wait a bit for dynamic content
            await self.page.wait_for_timeout(3000)

            # Scroll down to load more results (lazy loading)
            for _ in range(3):
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await self.page.wait_for_timeout(2000)
                
            # Parse the results
            # Note: Facebook CSS classes are obfuscated and change often. 
            # A common pattern is looking for links with '/marketplace/item/'
            items = self.page.locator('a[href*="/marketplace/item/"]')
            count = await items.count()
            
            for i in range(count):
                item = items.nth(i)
                try:
                    url = await item.get_attribute('href')
                    if url.startswith('/'):
                        url = 'https://www.facebook.com' + url
                    
                    # Extract text inside the link block. We might get title, price, location.
                    # Because classes change, we grab all inner text and split it.
                    inner_text = await item.inner_text()
                    lines = [line.strip() for line in inner_text.split('\n') if line.strip()]
                    
                    title = "Unknown Title"
                    price = "Unknown Price"
                    location = "Unknown Location"
                    
                    # Usually: [Price, Title, Location] or similar depending on layout
                    if len(lines) >= 3:
                        price = lines[0]
                        title = lines[1]
                        location = lines[2]
                    elif len(lines) >= 2:
                        price = lines[0]
                        title = lines[1]
                        
                    results.append(SearchResult(
                        source='Facebook Marketplace',
                        title=title,
                        url=url,
                        price=price,
                        location=location
                    ))
                except Exception as e:
                    print(f'Error parsing an FB result: {e}')
                    continue
                    
        except Exception as e:
            print(f'Failed to search Facebook Marketplace: {e}')
            
        return results
