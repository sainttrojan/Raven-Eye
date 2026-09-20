with open("core/report_generator.py", "r", encoding="utf-8") as f:
    content = f.read()

excel_old = """            # DB Correlation
            corr = data.get("db_correlation", {})
            if corr and corr.get("ok") and corr.get("count", 0) > 0:
                df_corr = pd.DataFrame(corr.get("listings", []))
                df_corr.to_excel(writer, sheet_name="Previous Listings", index=False)"""

excel_new = """            # DB Correlation
            corr = data.get("db_correlation", {})
            if corr and corr.get("ok") and corr.get("count", 0) > 0:
                df_corr = pd.DataFrame(corr.get("listings", []))
                df_corr.to_excel(writer, sheet_name="Previous Listings", index=False)
                
            # Web Footprint (Google)
            wres = data.get("web_footprint", {})
            if wres and wres.get("ok") and wres.get("count", 0) > 0:
                df_wres = pd.DataFrame(wres.get("items", []))
                df_wres.to_excel(writer, sheet_name="Web Footprint", index=False)"""

content = content.replace(excel_old, excel_new)

pdf_old = """        corr = data.get("db_correlation", {})
        if corr and corr.get("ok") and corr.get("count", 0) > 0:
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, f"Found {corr.get('count')} times in Database (Previous Listings):", ln=True)
            pdf.set_font("Arial", size=10)
            for li in corr.get("listings", [])[:10]: # show top 10
                title = str(li.get("Title", ""))[:50].encode('ascii', 'ignore').decode() # strip arabic/emoji for basic pdf
                pdf.cell(0, 8, f"- {title} | {li.get('Price', '')}", ln=True)"""

pdf_new = """        corr = data.get("db_correlation", {})
        if corr and corr.get("ok") and corr.get("count", 0) > 0:
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, f"Found {corr.get('count')} times in Database (Previous Listings):", ln=True)
            pdf.set_font("Arial", size=10)
            for li in corr.get("listings", [])[:10]: # show top 10
                title = str(li.get("Title", ""))[:50].encode('ascii', 'ignore').decode() # strip arabic/emoji for basic pdf
                pdf.cell(0, 8, f"- {title} | {li.get('Price', '')}", ln=True)
                
        wres = data.get("web_footprint", {})
        if wres and wres.get("ok") and wres.get("count", 0) > 0:
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, f"Found {wres.get('count')} times in Google Search (Web Footprint):", ln=True)
            pdf.set_font("Arial", size=10)
            for it in wres.get("items", [])[:10]: # show top 10
                title = str(it.get("Title", ""))[:50].encode('ascii', 'ignore').decode()
                url = str(it.get("URL", ""))
                pdf.cell(0, 8, f"- {title}", ln=True)
                pdf.set_font("Arial", "U", 10)
                pdf.cell(0, 8, f"  {url}", ln=True)
                pdf.set_font("Arial", size=10)"""

content = content.replace(pdf_old, pdf_new)

with open("core/report_generator.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Report generator patched!")
