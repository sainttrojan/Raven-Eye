import re

with open("radar_loop.py", "r") as f:
    code = f.read()

pattern = r"def credits_btn\(message\):.*?except Exception as e:\n        bot\.reply_to\(message, \"حدث خطأ أثناء جلب الرصيد\.\"\)"

new_func = """def credits_btn(message):
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
            
        text = "📊 <b>إجمالي رصيد جميع الحسابات</b>\\n\\n🔹 المستخدم الكلي: {total_used}\\n🔹 المتبقي الكلي: <b>{total_rem}</b>\\n🔹 الحد الأقصى الكلي: {total_limit}"
        text = text.replace('{total_used}', str(total_used)).replace('{total_rem}', str(total_rem)).replace('{total_limit}', str(total_limit))
        
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء جلب الرصيد.")"""

# Note the actual new line character replacement to prevent SyntaxError
code = re.sub(pattern, new_func.replace('\\n', '\n'), code, flags=re.DOTALL)

with open("radar_loop.py", "w") as f:
    f.write(code)
