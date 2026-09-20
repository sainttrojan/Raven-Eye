import re

with open("scrapers/dubizzle.py", "r") as f:
    code = f.read()

# Remove the forced qdr:d fallback
code = code.replace('tf = time_filter if time_filter else "qdr:d"', 'tf = time_filter')

with open("scrapers/dubizzle.py", "w") as f:
    f.write(code)
