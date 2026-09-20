import re

with open("app.py", "r") as f:
    code = f.read()

# Add json import if not present
if "import json" not in code:
    code = "import json\nimport os\n" + code

# Function to get/set keys
key_utils = """
KEYS_FILE = "api_keys.json"

def get_active_keys():
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r") as f:
                keys = json.load(f)
                if keys: return keys
        except: pass
    env_keys = os.getenv("SCRAPER_API_KEYS", "")
    return [k.strip() for k in env_keys.split(",") if k.strip()]

def save_active_keys(keys_list):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys_list, f)
"""

code = code.replace("st.set_page_config", key_utils + "\nst.set_page_config")

# Update Scraper Instantiation in app.py
code = code.replace("DubizzleScraper(os.getenv('SCRAPER_API_KEY'))", "DubizzleScraper(get_active_keys())")
code = code.replace("DubizzleScraper([os.getenv('SCRAPER_API_KEY')])", "DubizzleScraper(get_active_keys())")

# Add Sidebar Settings
sidebar_code = """
with st.sidebar:
    st.header("⚙️ إعدادات النظام")
    current_keys = get_active_keys()
    keys_input = st.text_area("ScraperAPI Keys (مفتاح في كل سطر)", value="\\n".join(current_keys))
    if st.button("حفظ المفاتيح"):
        new_keys = [k.strip() for k in keys_input.split("\\n") if k.strip()]
        save_active_keys(new_keys)
        st.success("تم الحفظ بنجاح! سيتم استخدامها في البوت والموقع.")
        
    st.markdown("---")
"""

# Inject sidebar before the search button logic
code = re.sub(r"(st\.title.*?)\n(.*?)with st\.form\('search_form'\):", r"\1\n" + sidebar_code + r"\2\nwith st.form('search_form'):", code, flags=re.DOTALL)

with open("app.py", "w") as f:
    f.write(code)
