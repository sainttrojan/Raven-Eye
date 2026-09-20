import re

with open("radar_loop.py", "r") as f:
    code = f.read()

old_filter_pattern = r"def is_valid_result.*?return True"

new_filter = """def is_valid_result(r, query):
    text = (r.title + " " + r.description).lower()
    
    if "مدينتي" in query:
        if "مدينتي" not in text:
            return False
            
        bad_cities = ["الشروق", "بدر", "الرحاب", "المستقبل", "التجمع", "العاصمة", "العبور"]
        for bc in bad_cities:
            if bc in text:
                return False
                
    bad_keywords = ["شركة", "بروكر", "عمولة", "تسويق", "وسيط", "مكتب", "سمسار"]
    for bk in bad_keywords:
        if bk in text:
            return False
            
    return True"""

code = re.sub(old_filter_pattern, new_filter, code, flags=re.DOTALL)

with open("radar_loop.py", "w") as f:
    f.write(code)
