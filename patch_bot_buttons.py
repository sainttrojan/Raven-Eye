import re

with open("radar_loop.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update get_main_keyboard
old_keyboard = """    if str(chat_id) == ADMIN_CHAT_ID:
        item_status = types.KeyboardButton('📊 حالة الرادار')
        item_credits = types.KeyboardButton('💰 الرصيد')
        item_pause = types.KeyboardButton('⏸️ إيقاف الرادار')
        item_resume = types.KeyboardButton('▶️ تشغيل الرادار')
        item_restart = types.KeyboardButton('🔄 ريستارت')
        markup.add(item_search, item_status, item_credits, item_pause, item_resume, item_restart)"""

new_keyboard = """    if str(chat_id) == ADMIN_CHAT_ID:
        item_status = types.KeyboardButton('📊 حالة الرادار')
        item_credits = types.KeyboardButton('💰 الرصيد')
        item_pause = types.KeyboardButton('⏸️ إيقاف الرادار')
        item_resume = types.KeyboardButton('▶️ تشغيل الرادار')
        item_restart = types.KeyboardButton('🔄 ريستارت')
        item_broker = types.KeyboardButton('🕵️ فحص سمسار (OSINT)')
        item_phone = types.KeyboardButton('📱 فحص رقم (OSINT)')
        markup.row(item_search, item_status)
        markup.row(item_broker, item_phone)
        markup.row(item_credits, item_pause, item_resume)
        markup.row(item_restart)"""

content = content.replace(old_keyboard, new_keyboard)

# Add new handlers for OSINT buttons before if __name__ == "__main__":
osint_handlers = """
@bot.message_handler(func=lambda message: message.text in ['🕵️ فحص سمسار (OSINT)'])
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
    checkphone_cmd(message)

if __name__ == "__main__":"""

content = content.replace('if __name__ == "__main__":', osint_handlers)

with open("radar_loop.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patched successfully!")
