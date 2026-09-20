import re

with open("radar_loop.py", "r") as f:
    content = f.read()

# I will just write a python script that replaces the entire credits_btn function from scratch!
# To avoid any escaping issues, I will construct it safely.

safe_func = """def credits_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    bot.reply_to(message, "جاري فحص جميع الحسابات... ⏳")
    try:
        total_used = 0
        total_limit = 0
        total_rem = 0
        for key in SCRAPER_API_KEYS:
            try:
                resp = requests.get(f"http://api.scraperapi.com/account?api_key={key}", timeout=5)
                data = resp.json()
                used = data.get('requestCount', 0)
                limit = data.get('requestLimit', 0)
                total_used += used
                total_limit += limit
                total_rem += max(0, limit - used)
            except: pass
            
        lines = [
            "📊 <b>إجمالي رصيد جميع الحسابات</b>",
            "",
            f"🔹 المستخدم الكلي: {total_used}",
            f"🔹 المتبقي الكلي: <b>{total_rem}</b>",
            f"🔹 الحد الأقصى الكلي: {total_limit}"
        ]
        text = "\\n".join(lines)
        
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء جلب الرصيد.")
"""
# Replace the buggy function
pattern = r"def credits_btn\(message\):.*?except Exception as e:\n        bot\.reply_to\(message, \"حدث خطأ أثناء جلب الرصيد\.\"\)"

content = re.sub(pattern, safe_func.replace("\\n", "\n"), content, flags=re.DOTALL)

with open("radar_loop.py", "w") as f:
    f.write(content)
