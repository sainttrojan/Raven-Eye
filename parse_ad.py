from bs4 import BeautifulSoup

with open("dubizzle_test.html", "r") as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

links = soup.find_all('a', href=True)
for a in links:
    if '/ad/' in a['href']:
        print("Found /ad/ link! Parent tag:", a.parent.name)
        print("Parent's parent tag:", a.parent.parent.name)
        print("Classes of parent:", a.parent.get('class'))
        print("Classes of parent's parent:", a.parent.parent.get('class'))
        
        # Let's see what we can extract from a
        title = a.get('aria-label', a.get('title', 'Unknown'))
        if title == 'Unknown' or not title:
            title_elem = a.find('div', string=True)
            if title_elem: title = title_elem.text
        
        spans = a.find_all('span')
        texts = [s.text.strip() for s in spans if s.text.strip()]
        
        print("Title:", title)
        print("Texts:", texts)
        break
