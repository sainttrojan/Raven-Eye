import re

with open('scrapers/google.py', 'r') as f:
    content = f.read()

resolver_fallback = """    def resolve_google_url(self, url: str) -> str:
        if 'google.com/goto?url=' in url or 'google.com/url?q=' in url:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                resp = requests.get(url, headers=headers, allow_redirects=False, timeout=5)
                if resp.status_code in [301, 302, 303, 307, 308]:
                    return resp.headers.get('Location', url)
            except Exception:
                pass
                
            # Fallback to ScraperAPI if direct request fails (Streamlit Cloud IP blocked)
            try:
                current_api_key = self.api_keys[self.current_key_idx]
                api_url = f'http://api.scraperapi.com?api_key={current_api_key}&url={url}'
                resp = requests.get(api_url, allow_redirects=False, timeout=10)
                if resp.status_code in [301, 302, 303, 307, 308]:
                    return resp.headers.get('Location', url)
            except Exception:
                pass
                
        return url"""

content = re.sub(r'    def resolve_google_url\(self, url: str\) -> str:.*?return url', resolver_fallback, content, flags=re.DOTALL)

with open('scrapers/google.py', 'w') as f:
    f.write(content)
