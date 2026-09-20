with open("radar_loop.py", "r") as f:
    code = f.read()

code = code.replace('text=f"تم اختيار: {user_search_state[chat_id][\'site\']}\n\nاختار تاريخ النشر:"', 'text=f"تم اختيار: {user_search_state[chat_id][\'site\']}\\n\\nاختار تاريخ النشر:"')
code = code.replace('text=f"تم اختيار: {user_search_state[chat_id][\'time\']}\n\nهل تريد تطابق الجملة بالكامل؟"', 'text=f"تم اختيار: {user_search_state[chat_id][\'time\']}\\n\\nهل تريد تطابق الجملة بالكامل؟"')

# Also replace HTML breaks in the results text if they broke
code = code.replace('f"📌 <b>العنوان:</b> {r.title}\n"\n', 'f"📌 <b>العنوان:</b> {r.title}\\n"\n')
code = code.replace('f"💰 <b>السعر:</b> {price_text}\n"\n', 'f"💰 <b>السعر:</b> {price_text}\\n"\n')
code = code.replace('f"📏 <b>المساحة:</b> {area_text}\n"\n', 'f"📏 <b>المساحة:</b> {area_text}\\n"\n')
code = code.replace('f"📝 <b>التفاصيل:</b> {r.description}\n\n"\n', 'f"📝 <b>التفاصيل:</b> {r.description}\\n\\n"\n')

with open("radar_loop.py", "w") as f:
    f.write(code)
