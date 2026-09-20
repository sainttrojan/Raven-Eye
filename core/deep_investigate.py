"""Deep broker investigation: every identifier across every engine.

One call fans out to all lookup surfaces Raven-Eye knows:
  phone    -> phonenumbers offline + ignorant (amazon/instagram/snapchat)
              + internal DB correlation
  email    -> user-scanner full email scan (~200 modules, all categories)
  username -> user-scanner full username scan (~880 modules, all categories)
              + username guesses derived from the email local-part

Each engine only accepts its own identifier type (a phone number cannot be
sent to a username endpoint), so "all sites" coverage means running every
engine for the identifiers we have — which is exactly what this does.

Full scans are slow (several minutes). Callers should run this in the
background / with a spinner and a generous timeout.
"""

from typing import Any, Dict, List, Optional

from core.phone_osint import full_check as phone_full_check
from core.phone_osint import find_in_database as phone_find_in_db
from core.broker_osint import (
    guess_usernames_from_email,
    scan_email,
    scan_username,
)


def investigate(phone: str = "", email: str = "", username: str = "",
                phone_timeout: int = 20, scan_timeout: int = 1200,
                allow_loud: bool = False, cross_scan: bool = False,
                email_modules: Optional[str] = None,
                username_modules: Optional[str] = None,
                db=None) -> Dict[str, Any]:
    """Run every applicable engine. Empty strings are skipped.

    email_modules/username_modules limit the user-scanner scope (fast tests);
    None means FULL scan of all sites.
    Returns {"phone": {...}|None, "email": {...}|None,
             "usernames": [...], "summary": {...}}.
    """
    phone = (phone or "").strip()
    email = (email or "").strip()
    username = (username or "").strip()

    report: Dict[str, Any] = {"phone": None, "email": None, "usernames": [],
                              "summary": {}}
    total_hits = 0

    if phone:
        pres = phone_full_check(phone, with_accounts=True, timeout=phone_timeout)
        if pres.get("ok"):
            try:
                corr = phone_find_in_db(phone, db)
            except Exception as e:
                corr = {"ok": False, "error": str(e)}
            pres["db_correlation"] = corr
            total_hits += sum(1 for a in pres.get("accounts", []) if a.get("exists"))
            total_hits += (corr.get("count", 0) if corr.get("ok") else 0)
        report["phone"] = pres

    if email:
        eres = scan_email(email, modules=email_modules, timeout=scan_timeout,
                          allow_loud=allow_loud, cross_scan=cross_scan)
        if eres.get("ok"):
            total_hits += eres.get("total_hits", 0)
            try:
                if db is None:
                    from core.db import DatabaseManager
                    db = DatabaseManager()
                db.save_osint_result("email", eres["target"], eres["total_hits"],
                                     eres.get("total_checked", 0), eres["hits"], "")
            except Exception:
                pass
        report["email"] = eres

    targets: List[str] = []
    if username:
        targets.append(username)
    if email:
        for g in guess_usernames_from_email(email):
            if g not in targets:
                targets.append(g)

    for u in targets:
        ures = scan_username(u, modules=username_modules, timeout=scan_timeout,
                             allow_loud=allow_loud, cross_scan=cross_scan)
        if ures.get("ok"):
            total_hits += ures.get("total_hits", 0)
            try:
                if db is None:
                    from core.db import DatabaseManager
                    db = DatabaseManager()
                db.save_osint_result("username", ures["target"], ures["total_hits"],
                                     ures.get("total_checked", 0), ures["hits"], "")
            except Exception:
                pass
        report["usernames"].append(ures)

    parts = []
    if report["phone"]:
        parts.append("phone")
    if report["email"]:
        parts.append("email")
    parts += [f"username:{u.get('target')}" for u in report["usernames"]]
    report["summary"] = {"engines": parts, "total_hits": total_hits}
    return report
