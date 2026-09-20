with open("radar_loop.py", "r") as f:
    code = f.read()

import re

old_filter_pattern = r"def is_valid_result.*?return True"

new_filter = """def is_valid_result(r, query):
    text = (r.title + " " + r.description).lower()
    
    if "مدينتي" in query:
        if "مدينتي" not in text:
            return False
            
        trick_phrases = [
            "بجوار مدينتي", "دقائق من مدينتي", "قريب من مدينتي", 
            "امام مدينتي", "أمام مدينتي", "بالقرب من مدينتي", "خطوات من مدينتي",
            "علي مدينتي", "على مدينتي", "تطل على مدينتي"
        ]
        for tp in trick_phrases:
            if tp in text:
                return False
                
        bad_cities = [
            "الشروق", "بدر", "الرحاب", "المستقبل", "التجمع", "العاصمة", "العبور", "هيليوبوليس",
            "القاهرة الجديدة", "new cairo", "ميفيدا", "mivida", "سوديك", "sodic", 
            "اللوتس", "الاندلس", "الأندلس", "النرجس", "البنفسج", "الياسمين", "القرنفل", 
            "المرشدي", "المراسم", "فيفث سكوير", "fifth square", "ماونتن فيو", "mountain view",
            "بالم هيلز", "palm hills", "سراي", "sarai", "تاج سيتي", "taj city", "زايد", "اكتوبر"
        ]
        for bc in bad_cities:
            if bc in text:
                return False
                
    bad_keywords = [
        "شركة", "بروكر", "عمولة", "تسويق", "وسيط", "مكتب", "سمسار", "عقارات", "broker", 
        "real estate", "بدون عموله", "بدون عمولة", "شهر مجانا"
    ]
    for bk in bad_keywords:
        if bk in text:
            return False
            
    return True"""

code = re.sub(old_filter_pattern, new_filter, code, flags=re.DOTALL)

with open("radar_loop.py", "w") as f:
    f.write(code)
