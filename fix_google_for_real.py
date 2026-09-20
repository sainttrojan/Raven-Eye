with open('scrapers/google.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if "url_lower = url.lower()" in line and "is_valid_listing" in lines[i-2]:
        new_lines.append(line)
        new_lines.append("        if 'google.com/goto' in url_lower or 'google.com/url' in url_lower:\n            return False\n")
    elif "link = item.get('link')" in line:
        new_lines.append(line)
        new_lines.append("                        link = self.resolve_google_url(link)\n")
    else:
        new_lines.append(line)

with open('scrapers/google.py', 'w') as f:
    f.writelines(new_lines)
