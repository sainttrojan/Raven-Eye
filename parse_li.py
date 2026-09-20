from bs4 import BeautifulSoup

with open("dubizzle_test.html", "r") as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

links = soup.find_all('a', href=True)
for a in links:
    if '/ad/' in a['href']:
        # Find the outermost <li>
        li = a.find_parent('li')
        if li:
            print("Found <li>!")
            title = li.get('aria-label', a.get('title', 'Unknown'))
            if title == 'Unknown' or not title:
                title_elem = li.find('div', string=True)
                if title_elem: title = title_elem.text
            
            spans = li.find_all('span')
            texts = [s.text.strip() for s in spans if s.text.strip()]
            
            print("Title:", title)
            print("Texts:", texts)
            break
