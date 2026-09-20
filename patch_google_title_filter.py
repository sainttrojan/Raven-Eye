import re

with open('scrapers/google.py', 'r') as f:
    content = f.read()

# 1. Remove the dropping of google.com/goto in is_valid_listing
content = content.replace("        if 'google.com/goto' in url_lower or 'google.com/url' in url_lower:\n            return False\n", "")

# 2. Add is_category_title function
category_filter = """    def is_category_title(self, title: str) -> bool:
        if not title: return False
        t = title.lower()
        # Branding suffixes usually present on category pages
        if '| دوبيزل' in t or '| dubizzle' in t or '(olx)' in t: return True
        if '- property finder' in t or '| property finder' in t: return True
        if '- aqarmap' in t or '| aqarmap' in t: return True
        
        # Generic SEO titles
        if t.startswith('شقق للبيع في') or t.startswith('شقق للإيجار في'): return True
        if t.startswith('apartments for') or t.startswith('properties for'): return True
        if t.startswith('villas for') or t.startswith('عقارات'): return True
        if t == 'شقق للبيع في مدينتي من المالك': return True
        return False

    def is_valid_listing"""

content = content.replace("    def is_valid_listing", category_filter)

# 3. Add the check in the loop
loop_update = """                        if title and link:
                            if self.is_category_title(title):
                                continue
                            if 'google.com/goto' not in link and 'google.com/url' not in link:
                                if not self.is_valid_listing(link):
                                    continue"""
content = content.replace("""                        if title and link:
                            if not self.is_valid_listing(link):
                                continue""", loop_update)

with open('scrapers/google.py', 'w') as f:
    f.write(content)
