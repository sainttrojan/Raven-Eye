import json
from core.broker_osint import scan_email
import warnings
warnings.filterwarnings('ignore')

print("Starting deep scan on test email...")
res = scan_email("testbroker99@gmail.com", modules=None, timeout=60, cross_scan=True, allow_loud=True)
print("Hits found:", res.get("total_hits"))
print("Checked:", res.get("total_checked"))
print(json.dumps(res.get("hits", [])[:3], indent=2))
