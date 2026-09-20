with open("radar_loop.py", "r") as f:
    code = f.read()

escape_func = """def escape_html(text):
    if not text: return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

"""

if "def escape_html" not in code:
    code = code.replace("def is_valid_result", escape_func + "def is_valid_result")

# Update run_radar_iteration
code = code.replace('f"📌 <b>العنوان:</b> {r.title}\\n"', 'f"📌 <b>العنوان:</b> {escape_html(r.title)}\\n"')
code = code.replace('f"📝 <b>التفاصيل:</b> {r.description}\\n\\n"', 'f"📝 <b>التفاصيل:</b> {escape_html(r.description)}\\n\\n"')

with open("radar_loop.py", "w") as f:
    f.write(code)
