import os
import pandas as pd
from fpdf import FPDF
from typing import Dict, Any, List

def generate_osint_excel(data: Dict[str, Any], kind: str, target: str, filename: str):
    with pd.ExcelWriter(filename) as writer:
        if kind in ("email", "username"):
            hits = data.get("hits", [])
            if hits:
                df = pd.DataFrame(hits)
                df.to_excel(writer, sheet_name="Results", index=False)
            else:
                pd.DataFrame([{"Result": "No hits found"}]).to_excel(writer, sheet_name="Results", index=False)
        elif kind == "phone":
            # Phone details
            df_info = pd.DataFrame([{
                "Phone": data.get("e164", target),
                "Carrier": data.get("carrier", "N/A"),
                "Valid": data.get("valid", False),
            }])
            df_info.to_excel(writer, sheet_name="Info", index=False)
            
            # Accounts
            accs = data.get("accounts", [])
            if accs:
                df_accs = pd.DataFrame(accs)
                df_accs.to_excel(writer, sheet_name="Accounts", index=False)
                
            # Links
            links = data.get("links", {})
            if links:
                df_links = pd.DataFrame([{"Platform": k, "URL": v} for k, v in links.items()])
                df_links.to_excel(writer, sheet_name="Links", index=False)
                
            # DB Correlation
            corr = data.get("db_correlation", {})
            if corr and corr.get("ok") and corr.get("count", 0) > 0:
                df_corr = pd.DataFrame(corr.get("listings", []))
                df_corr.to_excel(writer, sheet_name="Previous Listings", index=False)
                
            # Web Footprint (Google)
            wres = data.get("web_footprint", {})
            if wres and wres.get("ok") and wres.get("count", 0) > 0:
                df_wres = pd.DataFrame(wres.get("items", []))
                df_wres.to_excel(writer, sheet_name="Web Footprint", index=False)

def generate_osint_pdf(data: Dict[str, Any], kind: str, target: str, filename: str):
    pdf = FPDF()
    pdf.add_page()
    
    # Try to use a unicode font if available, fallback to Arial.
    # Note: for Arabic we'd need a specific font and bidi, but we'll use English keys for the report structure
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"OSINT Report: {target}", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    
    if kind in ("email", "username"):
        pdf.cell(0, 10, f"Target Type: {kind}", ln=True)
        pdf.cell(0, 10, f"Total Hits: {data.get('total_hits', 0)} out of {data.get('total_checked', 0)}", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Found on Sites:", ln=True)
        pdf.set_font("Arial", size=10)
        
        for hit in data.get("hits", []):
            pdf.cell(0, 8, f"- {hit.get('site_name', 'Unknown')}: {hit.get('url', '')}", ln=True)
            
    elif kind == "phone":
        pdf.cell(0, 10, f"Target Type: Phone", ln=True)
        pdf.cell(0, 10, f"Formatted: {data.get('e164', target)}", ln=True)
        pdf.cell(0, 10, f"Carrier: {data.get('carrier', 'N/A')}", ln=True)
        pdf.cell(0, 10, f"Valid: {'Yes' if data.get('valid') else 'No'}", ln=True)
        pdf.ln(5)
        
        accs = data.get("accounts", [])
        if accs:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Registered Accounts:", ln=True)
            pdf.set_font("Arial", size=10)
            for acc in accs:
                status = "Exists" if acc.get("exists") else ("Rate Limited" if acc.get("rate_limited") else "Not found")
                pdf.cell(0, 8, f"- {acc.get('domain', 'Unknown')}: {status}", ln=True)
            pdf.ln(5)
            
        links = data.get("links", {})
        if links:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Direct Deep Links:", ln=True)
            pdf.set_font("Arial", size=10)
            for platform, url in links.items():
                pdf.cell(0, 8, f"- {platform.capitalize()}: {url}", ln=True)
                
        corr = data.get("db_correlation", {})
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
                pdf.set_font("Arial", size=10)

    pdf.output(filename)

