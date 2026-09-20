import re

with open("radar_loop.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add user_osint_state at the top
content = content.replace("user_search_state = {}", "user_search_state = {}\nuser_osint_state = {}")

# 2. Replace the old UI handlers for checkphone and investigate
old_ui_handlers = """@bot.message_handler(func=lambda message: message.text in ['🕵️ فحص سمسار (OSINT)'])
def investigate_ui_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    msg = bot.reply_to(message, "ابعت اليوزرنيم أو الإيميل بتاع السمسار اللي عايز تفحصه:\\n(مثال: broker_name أو mail@example.com)")
    bot.register_next_step_handler(msg, step_investigate_ui)

def step_investigate_ui(message):
    if not message.text: return
    val = message.text.strip()
    kind = "email" if "@" in val else "username"
    # Construct a dummy message and call the original investigate_cmd
    message.text = f"/investigate {kind} {val}"
    investigate_cmd(message)

@bot.message_handler(func=lambda message: message.text in ['📱 فحص رقم (OSINT)'])
def checkphone_ui_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    msg = bot.reply_to(message, "ابعت رقم الموبايل اللي عايز تفحصه:\\n(مثال: 01001234567)")
    bot.register_next_step_handler(msg, step_checkphone_ui)

def step_checkphone_ui(message):
    if not message.text: return
    val = message.text.strip()
    # Construct a dummy message and call the original checkphone_cmd
    message.text = f"/checkphone {val}"
    checkphone_cmd(message)"""

new_ui_handlers = """@bot.message_handler(func=lambda message: message.text in ['🕵️ فحص سمسار (OSINT)'])
def investigate_ui_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    msg = bot.reply_to(message, "ابعت اليوزرنيم أو الإيميل بتاع السمسار اللي عايز تفحصه:\\n(مثال: broker_name أو mail@example.com)")
    bot.register_next_step_handler(msg, step_investigate_target)

def step_investigate_target(message):
    if not message.text: return
    chat_id = str(message.chat.id)
    val = message.text.strip()
    kind = "email" if "@" in val else "username"
    user_osint_state[chat_id] = {"type": "investigate", "kind": kind, "target": val}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("سريع (أشهر المواقع فقط - 30 ثانية)", callback_data="osint_inv_fast"),
        types.InlineKeyboardButton("عميق (كل المواقع - قد يستغرق دقائق)", callback_data="osint_inv_deep")
    )
    bot.send_message(message.chat.id, "اختار نوع الفحص:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('osint_inv_'))
def step_investigate_type(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_osint_state: return
    is_deep = call.data == "osint_inv_deep"
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="جاري بدء الفحص... ⏳")
    
    msg = call.message
    msg.text = f"/investigate {user_osint_state[chat_id]['kind']} {user_osint_state[chat_id]['target']} {'deep' if is_deep else 'fast'}"
    threading.Thread(target=investigate_cmd, args=(msg,)).start()


@bot.message_handler(func=lambda message: message.text in ['📱 فحص رقم (OSINT)'])
def checkphone_ui_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    msg = bot.reply_to(message, "ابعت رقم الموبايل اللي عايز تفحصه:\\n(مثال: 01001234567)")
    bot.register_next_step_handler(msg, step_checkphone_target)

def step_checkphone_target(message):
    if not message.text: return
    chat_id = str(message.chat.id)
    val = message.text.strip()
    user_osint_state[chat_id] = {"type": "checkphone", "target": val}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("عادي (بيانات وحسابات فقط)", callback_data="osint_ph_normal"),
        types.InlineKeyboardButton("شامل + جوجل (البحث عن الرقم فالويب)", callback_data="osint_ph_web")
    )
    bot.send_message(message.chat.id, "اختار نوع الفحص:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('osint_ph_'))
def step_checkphone_type(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_osint_state: return
    with_web = call.data == "osint_ph_web"
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="جاري بدء الفحص... ⏳")
    
    msg = call.message
    msg.text = f"/checkphone {user_osint_state[chat_id]['target']} {'with_web' if with_web else 'normal'}"
    threading.Thread(target=checkphone_cmd, args=(msg,)).start()
"""

if old_ui_handlers in content:
    content = content.replace(old_ui_handlers, new_ui_handlers)
else:
    print("Warning: old UI handlers not found exactly.")


# 3. Replace the old investigate_cmd logic
old_inv_logic = """        from core.broker_osint import scan_username, scan_email
        if kind == "email":
            res = scan_email(value, modules="github,instagram,facebook", timeout=300)
        else:
            res = scan_username(value, modules="github,instagram,facebook", timeout=300)"""

new_inv_logic = """        is_deep = len(parts) > 3 and parts[3].lower() == "deep"
        modules_arg = None if is_deep else "github,instagram,facebook,tiktok,twitter,snapchat,telegram"
        
        from core.broker_osint import scan_username, scan_email
        if kind == "email":
            res = scan_email(value, modules=modules_arg, timeout=600 if is_deep else 300)
        else:
            res = scan_username(value, modules=modules_arg, timeout=600 if is_deep else 300)"""

if old_inv_logic in content:
    content = content.replace(old_inv_logic, new_inv_logic)
else:
    print("Warning: old_inv_logic not found.")

# 4. Replace the old checkphone_cmd logic
old_checkphone_logic = """        try:
            corr = find_in_database(parts[1].strip())
            if corr.get("ok"):
                if corr["count"]:
                    lines.append(f"ظهر في {corr['count']} إعلان محفوظ عندنا")
                else:
                    lines.append("مش موجود في إعلاناتنا المحفوظة (معلن جديد غالبا)")
        except Exception:
            pass
        links = res.get("links", {})"""

new_checkphone_logic = """        try:
            corr = find_in_database(parts[1].strip())
            if corr.get("ok"):
                if corr["count"]:
                    lines.append(f"ظهر في {corr['count']} إعلان محفوظ عندنا")
                else:
                    lines.append("مش موجود في إعلاناتنا المحفوظة (معلن جديد غالبا)")
        except Exception:
            pass
            
        with_web = len(parts) > 2 and parts[2].lower() == "with_web"
        if with_web:
            lines.append("جاري البحث في جوجل... 🔍")
            try:
                from core.phone_osint import web_footprint
                from core.config import load_api_keys
                wres = web_footprint(parts[1].strip(), load_api_keys(), max_pages=2)
                res["web_footprint"] = wres
                if wres.get("ok") and wres.get("count") > 0:
                    lines.append(f"تم العثور على {wres['count']} نتيجة في جوجل!")
                elif wres.get("ok"):
                    lines.append("لا يوجد ظهور للرقم في جوجل.")
                else:
                    lines.append("تعذر البحث في جوجل.")
            except Exception as we:
                print("Web footprint error:", we)

        links = res.get("links", {})"""

if old_checkphone_logic in content:
    content = content.replace(old_checkphone_logic, new_checkphone_logic)
else:
    print("Warning: old_checkphone_logic not found.")


with open("radar_loop.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Rewrite OSINT done!")
