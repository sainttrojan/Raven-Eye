"""One-way sync: local database -> Google Sheet (leads distribution).

Each saved listing becomes one sheet row with its save date; rows already
in the sheet (matched by URL) are never duplicated. The team distributes
leads from the sheet itself (add assignee/status columns there freely —
sync only appends new rows and never touches existing ones).

Auth: a Google Cloud *service account* JSON key. Create it once in
Google Cloud Console (IAM > Service Accounts > Keys), download the JSON,
and share the target sheet with the service account's client_email as
Editor. Point the app at the file via Settings tab or the
GOOGLE_CREDENTIALS_FILE env var.
"""

import os
from typing import Any, Dict, List

HEADERS = ["Date Added", "Title", "Price", "Area", "Phone Number",
           "Advertiser", "Author", "Source", "URL", "Description", "Status"]

SHEET_SALE = "Sale"
SHEET_RENT = "Rent"
SHEET_OTHER = "Other"
SHEET_OSINT = "OSINT"
SHEET_WA_LOG = "WA Log"

OSINT_HEADERS = ["Date", "Kind", "Target", "Hits", "Checked", "Details", "Status"]
WA_HEADERS = ["Date", "Target", "Status", "Note", "Message"]


def lead_type(prop: Dict[str, Any]) -> str:
    """sale | rent | other, from listing text."""
    from core.listing_classifier import _norm
    blob = _norm(f"{prop.get('Title', '')}\n{prop.get('Description', '')}")
    rent_words = ["ايجار", "للايجار", "للإيجار", "مفروش", "شهري", "rent", "lease"]
    sale_words = ["بيع", "للبيع", "تمليك", "ريسيل", "resale", "sale", "قسط", "كاش"]
    rent_hit = any(w in blob for w in rent_words)
    sale_hit = any(w in blob for w in sale_words)
    if rent_hit and not sale_hit:
        return "rent"
    if sale_hit and not rent_hit:
        return "sale"
    if rent_hit and sale_hit:
        return "rent" if blob.find("ايجار") < blob.find("بيع") else "sale"
    return "other"


def build_row(prop: Dict[str, Any]) -> List[str]:
    """One property dict -> sheet row (all strings, Status defaults to new)."""
    return [
        str(prop.get("Added On", "") or ""),
        str(prop.get("Title", "") or ""),
        str(prop.get("Price", "") or ""),
        str(prop.get("Area", "") or ""),
        str(prop.get("Phone Number", "") or ""),
        str(prop.get("Owner Label", "") or ""),
        str(prop.get("Author", "") or ""),
        str(prop.get("Source", "") or ""),
        str(prop.get("URL", "") or ""),
        str(prop.get("Description", "") or "")[:1000],
        "new",
    ]


def _client(creds_file: str):
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    return gspread.authorize(creds)


def _worksheet(client, sheet_id: str, name: str = SHEET_SALE,
               headers: List[str] = HEADERS):
    try:
        sh = client.open_by_key(sheet_id)
    except Exception as e:
        raise RuntimeError(f"تعذر فتح الشيت (تأكد من الـ ID والمشاركة): {e}")
    try:
        ws = sh.worksheet(name)
    except Exception:
        ws = sh.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers)
        return ws
    values = ws.get_all_values()
    if not values:
        ws.append_row(headers)
    elif values[0] != headers:
        ws.insert_row(headers, 1)
    return ws


def existing_urls(ws) -> set:
    """URLs already in the sheet (URL column), for dedupe."""
    try:
        values = ws.get_all_values()
    except Exception:
        return set()
    if len(values) < 2:
        return set()
    try:
        idx = values[0].index("URL")
    except ValueError:
        return set()
    return {r[idx] for r in values[1:] if len(r) > idx and r[idx]}


def sync_database(db, sheet_id: str, creds_file: str) -> Dict[str, Any]:
    """Append new listings to Sale/Rent/Other sheets. Returns counts."""
    if not sheet_id or not sheet_id.strip():
        return {"ok": False, "error": "مفيش Sheet ID متسجل (تاب الإعدادات)"}
    if not creds_file or not os.path.exists(creds_file):
        return {"ok": False,
                "error": "ملف حساب الخدمة مش موجود (تاب الإعدادات)"}
    try:
        client = _client(creds_file)
        sid = sheet_id.strip()
        seen: set = set()
        sheets = {}
        for name in (SHEET_SALE, SHEET_RENT, SHEET_OTHER):
            ws = _worksheet(client, sid, name, HEADERS)
            sheets[name] = ws
            seen |= existing_urls(ws)
        props = db.get_all_properties()
        buckets: Dict[str, List[List[str]]] = {SHEET_SALE: [], SHEET_RENT: [],
                                               SHEET_OTHER: []}
        skipped = 0
        for p in props:
            if (p.get("URL") or "") in seen:
                skipped += 1
                continue
            t = lead_type(p)
            buckets[SHEET_RENT if t == "rent" else
                    SHEET_SALE if t == "sale" else SHEET_OTHER].append(build_row(p))
        pushed = 0
        for name, rows in buckets.items():
            if rows:
                sheets[name].append_rows(rows, value_input_option="USER_ENTERED")
                pushed += len(rows)
        return {"ok": True, "pushed": pushed, "skipped": skipped,
                "total": len(props),
                "by_sheet": {k: len(v) for k, v in buckets.items()}, "error": ""}
    except Exception as e:
        return {"ok": False, "error": f"فشلت المزامنة: {e}"}


def sync_osint(db, sheet_id: str, creds_file: str) -> Dict[str, Any]:
    """Append broker + phone investigations to the OSINT sheet."""
    if not sheet_id or not sheet_id.strip():
        return {"ok": False, "error": "مفيش Sheet ID متسجل (تاب الإعدادات)"}
    if not creds_file or not os.path.exists(creds_file):
        return {"ok": False,
                "error": "ملف حساب الخدمة مش موجود (تاب الإعدادات)"}
    try:
        from datetime import datetime
        ws = _worksheet(_client(creds_file), sheet_id.strip(),
                        SHEET_OSINT, OSINT_HEADERS)
        seen_targets = set()
        try:
            for row in ws.get_all_values()[1:]:
                if len(row) > 2:
                    seen_targets.add((row[1], row[2]))
        except Exception:
            pass
        rows = []
        for r in db.get_osint_results(limit=500):
            key = (str(r.get("target_type", "")), str(r.get("target", "")))
            if key in seen_targets:
                continue
            hits = r.get("hits", []) or []
            top = ", ".join(str(h.get("site_name", "")) for h in hits[:5])
            rows.append([str(r.get("created_at", "")), key[0], key[1],
                         str(r.get("total_hits", 0)),
                         str(r.get("total_checked", 0)), top, "new"])
            seen_targets.add(key)
        for r in db.get_phone_osint(limit=500):
            key = ("phone", str(r.get("phone", "")))
            if key in seen_targets:
                continue
            accs = r.get("accounts", []) or []
            top = ", ".join(a.get("domain", "") for a in accs if a.get("exists"))
            rows.append([str(r.get("created_at", "")), "phone", key[1],
                         str(len([a for a in accs if a.get("exists")])),
                         str(len(accs)), top or str(r.get("carrier", "")),
                         "new"])
            seen_targets.add(key)
        if rows:
            ws.append_rows(rows, value_input_option="USER_ENTERED")
        return {"ok": True, "pushed": len(rows), "error": "",
                "stamp": datetime.now().isoformat(timespec="seconds")}
    except Exception as e:
        return {"ok": False, "error": f"فشلت المزامنة: {e}"}


def log_wa_send(sheet_id: str, creds_file: str,
                results: List[Dict[str, Any]], message: str) -> Dict[str, Any]:
    """Append one WhatsApp run to the WA Log sheet (no dedupe — it's a log)."""
    if not sheet_id or not creds_file or not os.path.exists(creds_file or ""):
        return {"ok": False, "error": "الشيت غير مضبوط"}
    try:
        from datetime import datetime
        ws = _worksheet(_client(creds_file), sheet_id.strip(),
                        SHEET_WA_LOG, WA_HEADERS)
        stamp = datetime.now().isoformat(timespec="seconds")
        snippet = (message or "")[:200]
        rows = [[stamp, str(r.get("target", "")),
                 "sent" if r.get("ok") else "failed",
                 str(r.get("error", "") or ""), snippet] for r in results]
        if rows:
            ws.append_rows(rows, value_input_option="USER_ENTERED")
        return {"ok": True, "logged": len(rows), "error": ""}
    except Exception as e:
        return {"ok": False, "error": f"فشل التسجيل: {e}"}
