from bs4 import BeautifulSoup
with open("dubizzle_test.html", "r") as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
ad_links = soup.find_all('a', href=lambda href: href and '/ad/' in href)
print("Links found:", len(ad_links))
