import re

with open("radar_loop.py", "r", encoding="utf-8") as f:
    content = f.read()

# Modify investigate_cmd
old_investigate = """        try:
            from core.db import DatabaseManager
            DatabaseManager().save_osint_result(kind, value, res["total_hits"],
                                                res["total_checked"], hits, "")
        except Exception:
            pass
        bot.reply_to(message, "\\n".join(lines) or "لا توجد نتائج مؤكدة.")
    except Exception as e:"""

new_investigate = """        try:
            from core.db import DatabaseManager
            DatabaseManager().save_osint_result(kind, value, res["total_hits"],
                                                res["total_checked"], hits, "")
        except Exception:
            pass
        bot.reply_to(message, "\\n".join(lines) or "لا توجد نتائج مؤكدة.")
        
        try:
            from core.report_generator import generate_osint_excel, generate_osint_pdf
            import os
            
            bot.send_message(message.chat.id, "جاري تحضير ملفات الـ Excel والـ PDF... ⏳")
            excel_file = f"investigate_{value}.xlsx"
            pdf_file = f"investigate_{value}.pdf"
            
            generate_osint_excel(res, kind, value, excel_file)
            generate_osint_pdf(res, kind, value, pdf_file)
            
            with open(excel_file, "rb") as f_xls:
                bot.send_document(message.chat.id, f_xls)
            with open(pdf_file, "rb") as f_pdf:
                bot.send_document(message.chat.id, f_pdf)
                
            os.remove(excel_file)
            os.remove(pdf_file)
        except Exception as file_e:
            print("Failed to send files:", file_e)
            
    except Exception as e:"""

content = content.replace(old_investigate, new_investigate)


# Modify checkphone_cmd
old_checkphone = """        try:
            from core.db import DatabaseManager
            DatabaseManager().save_phone_osint(res["e164"], res.get("carrier", ""),
                                               bool(res.get("valid")), res.get("accounts", []), "")
        except Exception:
            pass
        bot.reply_to(message, "\\n".join(lines))
    except Exception as e:"""

new_checkphone = """        try:
            from core.db import DatabaseManager
            DatabaseManager().save_phone_osint(res["e164"], res.get("carrier", ""),
                                               bool(res.get("valid")), res.get("accounts", []), "")
        except Exception:
            pass
        bot.reply_to(message, "\\n".join(lines))
        
        try:
            from core.report_generator import generate_osint_excel, generate_osint_pdf
            import os
            
            if 'db_correlation' not in res:
                res['db_correlation'] = corr if 'corr' in locals() else {}
                
            bot.send_message(message.chat.id, "جاري تحضير ملفات الـ Excel والـ PDF... ⏳")
            excel_file = f"phone_{parts[1].strip()}.xlsx"
            pdf_file = f"phone_{parts[1].strip()}.pdf"
            
            generate_osint_excel(res, "phone", parts[1].strip(), excel_file)
            generate_osint_pdf(res, "phone", parts[1].strip(), pdf_file)
            
            with open(excel_file, "rb") as f_xls:
                bot.send_document(message.chat.id, f_xls)
            with open(pdf_file, "rb") as f_pdf:
                bot.send_document(message.chat.id, f_pdf)
                
            os.remove(excel_file)
            os.remove(pdf_file)
        except Exception as file_e:
            print("Failed to send files:", file_e)
            
    except Exception as e:"""

content = content.replace(old_checkphone, new_checkphone)

with open("radar_loop.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patched reports successfully!")
