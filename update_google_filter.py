import re

with open('scrapers/google.py', 'r') as f:
    content = f.read()

# Update resolver with User-Agent
resolver_new = """    def resolve_google_url(self, url: str) -> str:
        if 'google.com/goto?url=' in url or 'google.com/url?q=' in url:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                resp = requests.get(url, headers=headers, allow_redirects=False, timeout=10)
                if resp.status_code in [301, 302, 303, 307, 308]:
                    return resp.headers.get('Location', url)
            except Exception:
                pass
        return url"""

content = re.sub(r'    def resolve_google_url\(self, url: str\) -> str:.*?return url', resolver_new, content, flags=re.DOTALL)

# Update is_valid_listing to reject goto links
filter_new = """    def is_valid_listing(self, url: str) -> bool:
        url_lower = url.lower()
        
        if 'google.com/goto' in url_lower or 'google.com/url' in url_lower:
            return False"""
            
content = content.replace("    def is_valid_listing(self, url: str) -> bool:\n        url_lower = url.lower()", filter_new)

with open('scrapers/google.py', 'w') as f:
    f.write(content)
