import re

with open("radar_loop.py", "r") as f:
    code = f.read()

# Add TELEGRAM_TOKEN back to the code instead of os.getenv
code = code.replace('TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")', 'TELEGRAM_TOKEN = "8718465204:AAGvGQWwzEcwjSTKLQR4Uk27DYbVPy_V-Ps"')
code = code.replace('ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")', 'ADMIN_CHAT_ID = "8291802346"')

with open("radar_loop.py", "w") as f:
    f.write(code)

with open("scrapers/dubizzle.py", "r") as f:
    dcode = f.read()

# Add inurl:ad to the fallback query
dcode = dcode.replace('fallback_query = f"{query} site:dubizzle.com.eg"', 'fallback_query = f"{query} site:dubizzle.com.eg inurl:ad"')

with open("scrapers/dubizzle.py", "w") as f:
    f.write(dcode)

with open("scrapers/google.py", "r") as f:
    gcode = f.read()
    
# Fix the else indentation in google.py
# The else: is currently aligned with the for item in organic_results:
pattern = r"                else:\n                    print\(f\"ScraperAPI returned status code: \{response\.status_code\}\"\)\n                    break"
gcode = re.sub(pattern, "", gcode)

with open("scrapers/google.py", "w") as f:
    f.write(gcode)
