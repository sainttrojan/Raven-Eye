import telebot
try:
    bot = telebot.TeleBot(None)
    print("Success")
except Exception as e:
    print("Error:", e)
