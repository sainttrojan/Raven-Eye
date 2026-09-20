import requests

url = "https://www.google.com/goto?url=CAEStwEB6zswFb8-7v0fWlmv1M-Yt1ukcIYYe5r2bWZaFRzQryTo8vMAcPDwI0YvhbDk4pKz6i97p79FZyOrsudXKLJH6Yd-SZbsuLZSc20wh5_49Sr63bQQgPVBeYam0zS4YmoCSeFO3Tj-NrGfQnmEH14fyWManLLWp3WyprNh3rjHYnLTeA_u3Vcbfy0K0jmIdUefj-3_-0r-OBoxRiWdVY0QMZWFlXemwfSehRBVQ32F9rTwYWUfR7U"
api_url = f'http://api.scraperapi.com?api_key=efda9176f26841a181772cf1f7d5602c&url={url}'

try:
    resp = requests.get(api_url, allow_redirects=False, timeout=10)
    print("Status:", resp.status_code)
    print("Location:", resp.headers.get('Location'))
    if resp.status_code == 200:
        print("Body preview:", resp.text[:100])
except Exception as e:
    print(e)
