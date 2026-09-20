import requests
url = "https://www.google.com/goto?url=CAEStwEB6zswFb8-7v0fWlmv1M-Yt1ukcIYYe5r2bWZaFRzQryTo8vMAcPDwI0YvhbDk4pKz6i97p79FZyOrsudXKLJH6Yd-SZbsuLZSc20wh5_49Sr63bQQgPVBeYam0zS4YmoCSeFO3Tj-NrGfQnmEH14fyWManLLWp3WyprNh3rjHYnLTeA_u3Vcbfy0K0jmIdUefj-3_-0r-OBoxRiWdVY0QMZWFlXemwfSehRBVQ32F9rTwYWUfR7U"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
resp = requests.get(url, headers=headers, allow_redirects=False)
print("Status:", resp.status_code)
print("Headers:", resp.headers.get('Location'))
print("Body length:", len(resp.text))
if 'dubizzle' in resp.text:
    print("Found dubizzle in body")
