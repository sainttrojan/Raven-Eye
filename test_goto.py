import requests

url = "https://www.google.com/goto?url=CAESnQEB6zswFewG8hF6A3s29z24_t0_3CE_Ql5u_nQpqdHs4bNueF_PQtlkycfsIyf8-YLcw7D6i3Ob5p6iyA2qqfI_BVUHxGvOkmaZUnwvJRPMxdoL9m0HWbvd7Gpf3hYisJ79cJsqYZCykGjeR3tp6_gQnGr6gH5LwNYSUfY35TXPoeGz_czE721VwjVq3fxf2-qEcJn6XGnWXYYy86Xp"
try:
    resp = requests.head(url, allow_redirects=True, timeout=10)
    print("Final URL:", resp.url)
except Exception as e:
    print(e)
