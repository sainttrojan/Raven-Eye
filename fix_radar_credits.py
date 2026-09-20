with open("radar_loop.py", "r") as f:
    code = f.read()

old_func = """def background_radar():
    global radar_is_running
    while True:
        if radar_is_running:
            for q in DEFAULT_QUERIES:
                try:
                    run_radar_iteration(q)
                except Exception as e:
                    print("Radar Error:", e)
                time.sleep(10) # 10 seconds between different queries
        time.sleep(10800) # 3 hours"""

new_func = """def check_credits_internal():
    try:
        resp = requests.get(f"http://api.scraperapi.com/account?api_key={SCRAPER_API_KEY}")
        data = resp.json()
        used = data.get('requestCount', 0)
        limit = data.get('requestLimit', 0)
        return limit - used
    except:
        return 9999

def background_radar():
    global radar_is_running
    warning_sent = False
    while True:
        if radar_is_running:
            rem = check_credits_internal()
            
            if rem <= 50 and not warning_sent:
                try:
                    bot.send_message(ADMIN_CHAT_ID, f"⚠️ <b>تحذير هام:</b>\nرصيدك في ScraperAPI يوشك على النفاذ! المتبقي: <b>{rem}</b> نقطة فقط.", parse_mode="HTML")
                except: pass
                warning_sent = True
            elif rem > 50:
                warning_sent = False
                
            if rem > 0:
                for q in DEFAULT_QUERIES:
                    try:
                        run_radar_iteration(q)
                    except Exception as e:
                        print("Radar Error:", e)
                    time.sleep(10) # 10 seconds between different queries
            else:
                print("Skipping radar run because credits are empty.")
        time.sleep(10800) # 3 hours"""

code = code.replace(old_func, new_func)

with open("radar_loop.py", "w") as f:
    f.write(code)
