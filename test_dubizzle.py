import requests
import urllib.parse
from bs4 import BeautifulSoup
import json

query = "شقة للبيع مدينتي"
encoded_query = urllib.parse.quote(query.replace(' ', '-'))
dubizzle_url = f"https://www.dubizzle.com.eg/properties/q-{encoded_query}/?page=1"
api_url = f'http://api.scraperapi.com?api_key=085a9eef6828dfd6bb77a6f30ca19b3b&url={dubizzle_url}'

response = requests.get(api_url)
print("Status:", response.status_code)
soup = BeautifulSoup(response.text, 'html.parser')
script = soup.find('script', id='__NEXT_DATA__')
if script:
    print("Found NEXT DATA")
    try:
        data = json.loads(script.string)
        print("Keys:", data.keys())
    except Exception as e:
        print(e)
else:
    print("No NEXT DATA")
