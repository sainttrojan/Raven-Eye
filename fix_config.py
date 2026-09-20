with open("core/config.py", "r") as f:
    code = f.read()

old_keys = 'keys = ["06ede5861ed79f12ad4ed6f275ce0038"]'
new_keys = 'keys = [\n            "085a9eef6828dfd6bb77a6f30ca19b3b",\n            "af5da6333540757495114e2c35cf685d",\n            "df094a68b9768ecf6a694cd4ab045fdb",\n            "15428b0bc961dc879128ca2e8db2ab61",\n            "efda9176f26841a181772cf1f7d5602c"\n        ]'

code = code.replace(old_keys, new_keys)

with open("core/config.py", "w") as f:
    f.write(code)
