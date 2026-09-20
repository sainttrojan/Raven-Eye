with open("radar_loop.py", "r") as f:
    code = f.read()

old_filter = "def is_valid_result(r, query):\n    return True"

new_filter = """def is_valid_result(r, query):
    if r.price:
        import re
        digits = re.sub(r'[^0-9]', '', str(r.price))
        if digits:
            try:
                if int(digits) <= 12000:
                    return False
            except:
                pass
    return True"""

code = code.replace(old_filter, new_filter)

with open("radar_loop.py", "w") as f:
    f.write(code)
