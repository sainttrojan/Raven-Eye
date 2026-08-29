import os
from dotenv import load_dotenv

load_dotenv()

FB_EMAIL = os.getenv('FB_EMAIL')
FB_PASSWORD = os.getenv('FB_PASSWORD')

# We will store cookies here so we don't have to login every time
FB_COOKIES_FILE = 'fb_cookies.json'
