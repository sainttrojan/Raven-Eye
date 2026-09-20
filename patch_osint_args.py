with open("radar_loop.py", "r", encoding="utf-8") as f:
    content = f.read()

old_logic = """        from core.broker_osint import scan_username, scan_email
        if kind == "email":
            res = scan_email(value, modules=modules_arg, timeout=600 if is_deep else 300)
        else:
            res = scan_username(value, modules=modules_arg, timeout=600 if is_deep else 300)"""

new_logic = """        from core.broker_osint import scan_username, scan_email
        if kind == "email":
            res = scan_email(value, modules=modules_arg, timeout=900 if is_deep else 300, cross_scan=is_deep, allow_loud=is_deep)
        else:
            res = scan_username(value, modules=modules_arg, timeout=900 if is_deep else 300, cross_scan=is_deep, allow_loud=is_deep)"""

content = content.replace(old_logic, new_logic)

with open("radar_loop.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched!")
