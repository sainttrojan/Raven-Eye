import re

with open("radar_loop.py", "r") as f:
    code = f.read()

# Disable filtering completely
code = re.sub(r"def is_valid_result\(r, query\):.*?return True", "def is_valid_result(r, query):\n    return True", code, flags=re.DOTALL)

# Now, we need to inject the interactive search logic
# First, add the state dictionary at the top
code = code.replace("radar_is_running = True", "radar_is_running = True\nuser_search_state = {}")

# Also we need to import GoogleScraper in radar_loop.py
if "from scrapers.google import GoogleScraper" not in code:
    code = code.replace("from scrapers.dubizzle import DubizzleScraper", "from scrapers.dubizzle import DubizzleScraper\nfrom scrapers.google import GoogleScraper")

# Replace manual_search_btn and process_search_query
interactive_code = """
@bot.message_handler(func=lambda message: message.text in ['🔍 بحث جديد', '/search'])
def manual_search_btn(message):
    chat_id = str(message.chat.id)
    user_search_state[chat_id] = {}
    msg = bot.reply_to(message, "اكتب الكلمة اللي عايز تبحث عنها (مثال: شقة للبيع مدينتي):")
    bot.register_next_step_handler(msg, step_keyword)

def step_keyword(message):
    chat_id = str(message.chat.id)
    if not message.text: return
    user_search_state[chat_id]['query'] = message.text.strip()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("جميع المواقع", callback_data="site_all"),
        types.InlineKeyboardButton("Dubizzle فقط", callback_data="site_dubizzle"),
        types.InlineKeyboardButton("PropertyFinder فقط", callback_data="site_pf"),
        types.InlineKeyboardButton("Aqarmap فقط", callback_data="site_aqarmap")
    )
    bot.send_message(message.chat.id, "اختار الموقع اللي عايز تبحث فيه:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('site_'))
def step_site(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_search_state: return
    
    site_map = {
        "site_all": "جميع المواقع",
        "site_dubizzle": "Dubizzle فقط",
        "site_pf": "PropertyFinder فقط",
        "site_aqarmap": "Aqarmap فقط"
    }
    user_search_state[chat_id]['site'] = site_map.get(call.data, "جميع المواقع")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("أي وقت", callback_data="time_any"),
        types.InlineKeyboardButton("آخر 24 ساعة", callback_data="time_24h"),
        types.InlineKeyboardButton("آخر أسبوع", callback_data="time_week")
    )
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=f"تم اختيار: {user_search_state[chat_id]['site']}\\n\\nاختار تاريخ النشر:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def step_time(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_search_state: return
    
    time_map = {
        "time_any": "أي وقت",
        "time_24h": "آخر 24 ساعة",
        "time_week": "آخر أسبوع"
    }
    user_search_state[chat_id]['time'] = time_map.get(call.data, "أي وقت")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("نعم، تطابق حرفي", callback_data="exact_yes"),
        types.InlineKeyboardButton("لا، بحث عادي", callback_data="exact_no")
    )
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=f"تم اختيار: {user_search_state[chat_id]['time']}\\n\\nهل تريد تطابق الجملة بالكامل؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('exact_'))
def step_exact(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_search_state: return
    
    exact = True if call.data == "exact_yes" else False
    user_search_state[chat_id]['exact'] = exact
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="جاري البحث بناءً على اختياراتك... ⏳")
    
    # Run the search asynchronously
    threading.Thread(target=execute_custom_search, args=(chat_id, user_search_state[chat_id])).start()

def execute_custom_search(chat_id, state):
    query = state['query']
    site_option = state['site']
    time_option = state['time']
    exact_match = state['exact']
    
    final_query = query
    if exact_match:
        final_query = f'"{query}"'
        
    if site_option == "PropertyFinder فقط":
        final_query += " site:propertyfinder.eg"
    elif site_option == "Dubizzle فقط":
        # Dubizzle is handled separately, but for Google fallback we need the site parameter
        pass 
    elif site_option == "Aqarmap فقط":
        final_query += " site:aqarmap.com.eg"
        
    time_filter = ""
    if time_option == "آخر 24 ساعة":
        time_filter = "qdr:d"
    elif time_option == "آخر أسبوع":
        time_filter = "qdr:w"
        
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def fetch():
            if site_option == "Dubizzle فقط":
                scraper = DubizzleScraper(load_api_keys())
                return await scraper.search(query, time_filter, max_pages=3)
            else:
                scraper = GoogleScraper(load_api_keys())
                return await scraper.search(final_query, time_filter, max_pages=3)
                
        results = loop.run_until_complete(fetch())
        
        if results:
            bot.send_message(chat_id, f"✅ تم العثور على {len(results)} نتائج. جاري إرسالها...")
            for r in results[:15]: # Limit to 15 to avoid telegram spam
                price_text = r.price if r.price else "غير محدد"
                area_text = r.area if r.area else "غير محدد"
                msg = (
                    f"📌 <b>العنوان:</b> {r.title}\\n"
                    f"💰 <b>السعر:</b> {price_text}\\n"
                    f"📏 <b>المساحة:</b> {area_text}\\n"
                    f"📝 <b>التفاصيل:</b> {r.description}\\n\\n"
                    f"🔗 <a href='{r.url}'>رابط الإعلان</a>"
                )
                bot.send_message(chat_id, msg, parse_mode="HTML")
                time.sleep(1)
            if len(results) > 15:
                bot.send_message(chat_id, f"تم إخفاء {len(results) - 15} نتيجة إضافية لتجنب الإزعاج.")
        else:
            bot.send_message(chat_id, "❌ لم يتم العثور على أي نتائج مطابقة لاختياراتك.")
            
    except Exception as e:
        bot.send_message(chat_id, "⚠️ حدث خطأ أثناء البحث.")
        print(f"Custom Search Error: {e}")
"""

# Remove old manual_search_btn and process_search_query
code = re.sub(r"@bot\.message_handler\(func=lambda message: message\.text in \['🔍 بحث جديد', '/search'\]\).*?bot\.reply_to\(message, \"حدث خطأ أثناء البحث\.\"\)", interactive_code, code, flags=re.DOTALL)

with open("radar_loop.py", "w") as f:
    f.write(code)

