import re

with open('scrapers/google.py', 'r') as f:
    content = f.read()

# Add a resolver function
resolver = """
    def resolve_google_url(self, url: str) -> str:
        if 'google.com/goto?url=' in url or 'google.com/url?q=' in url:
            try:
                resp = requests.get(url, allow_redirects=False, timeout=10)
                if resp.status_code in [301, 302]:
                    return resp.headers.get('Location', url)
            except Exception:
                pass
        return url

    def is_valid_listing(self, url: str) -> bool:"""

content = content.replace("    def is_valid_listing(self, url: str) -> bool:", resolver)

# Update the loop to use it
loop_update = """                for item in organic_results:
                    raw_link = item.get('link', '')
                    resolved_link = self.resolve_google_url(raw_link)
                    item['link'] = resolved_link # update it
                    
                    if not self.is_valid_listing(resolved_link):
                        continue"""
content = re.sub(r'                for item in organic_results:\n                    if not self\.is_valid_listing\(item\.get\(\'link\', \'\'\)\):\n                        continue', loop_update, content)

with open('scrapers/google.py', 'w') as f:
    f.write(content)
