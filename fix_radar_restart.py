import os
import sys

with open("radar_loop.py", "r") as f:
    code = f.read()

new_command = """
@bot.message_handler(commands=['restart'])
def restart_bot(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    bot.reply_to(message, "جاري إعادة تشغيل نظام الرادار... 🔄")
    import sys
    import os
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.message_handler(commands=['status'])
"""

# Replace the @bot.message_handler(commands=['status']) with the new command + status
code = code.replace("@bot.message_handler(commands=['status'])", new_command.strip())

# Also update the help text
old_help = "/resume - إعادة تشغيل الرادار\n"
new_help = "/resume - إعادة تشغيل الرادار\n        /restart - عمل ريستارت كامل للبوت\n"
code = code.replace(old_help, new_help)

with open("radar_loop.py", "w") as f:
    f.write(code)
