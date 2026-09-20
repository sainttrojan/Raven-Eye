with open("radar_loop.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line == "user_search_state = {}\n" and not new_lines[-1].startswith("radar_is_running = True"):
        # This shouldn't happen based on the replace, wait.
        pass
        
    if "user_search_state = {}" in line:
        if line.startswith("user_search_state"):
            new_lines.append(line)
        else:
            # It was replaced inline like: "    radar_is_running = True\nuser_search_state = {}"
            # Actually, string.replace replaces ALL occurrences.
            pass
            
# Let's just fix it by reading the whole file, removing all `user_search_state = {}` and adding one at the top.
with open("radar_loop.py", "r") as f:
    code = f.read()

code = code.replace("\nuser_search_state = {}", "")
code = code.replace("user_search_state = {}\n", "")

# Now add it correctly at the top
code = code.replace("radar_is_running = True\n", "radar_is_running = True\nuser_search_state = {}\n", 1)

with open("radar_loop.py", "w") as f:
    f.write(code)
