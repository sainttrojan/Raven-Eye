import requests

url = "http://api.scraperapi.com?api_key=efda9176f26841a181772cf1f7d5602c&url=https://www.dubizzle.com.eg/properties/q-%D8%B4%D9%82%D8%A9-%D9%84%D9%84%D8%A8%D9%8A%D8%B9-%D9%85%D8%AF%D9%8A%D9%86%D8%AA%D9%8A/?page=1&render=true"
resp = requests.get(url, timeout=60)
with open("dubizzle_test.html", "w") as f:
    f.write(resp.text)
print("Saved to dubizzle_test.html")
