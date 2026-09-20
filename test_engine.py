import requests

api_url = "http://api.scraperapi.com?api_key=d868af7919cadbcc269fef0bfecff8e6&engine=google&q=site:dubizzle.com.eg"
try:
    resp = requests.get(api_url)
    print(resp.status_code)
    print(resp.text[:500])
except Exception as e:
    print(e)
