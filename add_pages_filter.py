import re

with open("radar_loop.py", "r") as f:
    code = f.read()

# Modify step_exact to ask for pages instead of starting thread
old_step_exact = """    exact = True if call.data == "exact_yes" else False
    user_search_state[chat_id]['exact'] = exact
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="جاري البحث بناءً على اختياراتك... ⏳")
    
    # Run the search asynchronously
    threading.Thread(target=execute_custom_search, args=(chat_id, user_search_state[chat_id])).start()"""

new_step_exact = """    exact = True if call.data == "exact_yes" else False
    user_search_state[chat_id]['exact'] = exact
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("1 صفحة (أسرع وأوفر)", callback_data="pages_1"),
        types.InlineKeyboardButton("3 صفحات", callback_data="pages_3"),
        types.InlineKeyboardButton("5 صفحات (دقيق)", callback_data="pages_5")
    )
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text="اختر عدد الصفحات التي تريد البحث فيها (كلما زاد العدد، زاد استهلاك الرصيد):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pages_'))
def step_pages(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_search_state: return
    
    pages = int(call.data.split('_')[1])
    user_search_state[chat_id]['pages'] = pages
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="جاري البحث بناءً على اختياراتك... ⏳")
    
    # Run the search asynchronously
    threading.Thread(target=execute_custom_search, args=(chat_id, user_search_state[chat_id])).start()"""

code = code.replace(old_step_exact, new_step_exact)

# Update execute_custom_search to use the pages
code = code.replace("def execute_custom_search(chat_id, state):", "def execute_custom_search(chat_id, state):\n    max_pages = state.get('pages', 3)")
code = code.replace("return await scraper.search(query, time_filter, max_pages=5)", "return await scraper.search(query, time_filter, max_pages=max_pages)")
code = code.replace("return await scraper.search(final_query, time_filter, max_pages=5)", "return await scraper.search(final_query, time_filter, max_pages=max_pages)")

with open("radar_loop.py", "w") as f:
    f.write(code)
