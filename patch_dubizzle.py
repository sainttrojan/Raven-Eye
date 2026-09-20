with open("scrapers/dubizzle.py", "r") as f:
    content = f.read()

old_code = """            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('article')
            if not articles:
                print(f"No articles found on page {page}.")
                break
                
            for a in articles:
                link_tag = a.find('a', href=True)
                if not link_tag: continue
                
                url = link_tag['href']
                if not url.startswith('http'):
                    url = "https://www.dubizzle.com.eg" + url
                    
                title = a.get('aria-label', link_tag.get('title', 'Unknown'))
                if title == 'Unknown' or not title:
                    title_elem = link_tag.find('div', string=True)
                    if title_elem: title = title_elem.text
                    
                spans = a.find_all('span')"""

new_code = """            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all a tags pointing to ads
            ad_links = soup.find_all('a', href=lambda href: href and '/ad/' in href)
            if not ad_links:
                print(f"No ad links found on page {page}.")
                break
                
            seen_urls = set()
            
            for link_tag in ad_links:
                url = link_tag['href']
                if not url.startswith('http'):
                    url = "https://www.dubizzle.com.eg" + url
                    
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                item = link_tag.find_parent('li')
                if not item:
                    item = link_tag.find_parent('div')
                    
                title = item.get('aria-label', link_tag.get('title', 'Unknown')) if item else 'Unknown'
                if title == 'Unknown' or not title:
                    title_elem = link_tag.find('div', string=True)
                    if title_elem: title = title_elem.text
                    
                spans = item.find_all('span') if item else link_tag.find_all('span')"""

content = content.replace(old_code, new_code)

with open("scrapers/dubizzle.py", "w") as f:
    f.write(content)
