"""Broker OSINT enrichment for Raven-Eye via user-scanner.

Raven-Eye scrapes property listings (title / description / URL / phone).
user-scanner maps a username or email to 1080+ platforms (Found / Registered).

This module is the glue between them:
  1. extract_contacts() pulls emails + social usernames out of a listing.
  2. scan_username() / scan_email() run user-scanner as a subprocess (CLI)
     so Raven-Eye's venv does NOT need user-scanner installed.
  3. enrich_property() does extract + scan in one call for a single listing.

Binary resolution order:
  USER_SCANNER_BIN env var > shutil.which("user-scanner") >
  /home/ahmed/Desktop/user-scanner/.venv/bin/user-scanner
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

DEFAULT_BIN = "/home/ahmed/Desktop/user-scanner/.venv/bin/user-scanner"

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# (platform label, regex with one capture group = username)
SOCIAL_PATTERNS = [
    ("facebook", re.compile(r"(?:facebook\.com/(?:profile\.php\?id=|people/)?)([A-Za-z0-9._]{3,50})", re.I)),
    ("instagram", re.compile(r"instagram\.com/([A-Za-z0-9._]{2,30})", re.I)),
    ("twitter", re.compile(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]{2,15})", re.I)),
    ("telegram", re.compile(r"t\.me/([A-Za-z0-9_]{3,32})", re.I)),
    ("tiktok", re.compile(r"tiktok\.com/@([A-Za-z0-9._]{2,30})", re.I)),
    ("linkedin", re.compile(r"linkedin\.com/in/([A-Za-z0-9-]{3,60})", re.I)),
    ("github", re.compile(r"github\.com/([A-Za-z0-9-]{2,39})", re.I)),
    ("youtube", re.compile(r"youtube\.com/(?:@|c/|channel/|user/)([A-Za-z0-9._-]{2,50})", re.I)),
    ("dubizzle_user", re.compile(r"dubizzle\.com[^\"'\s]*?(?:user|users|profile|member)[^\"'\s]*?/(\d{4,12})", re.I)),
]

HANDLE_RE = re.compile(r"(?<![\w@.])@([A-Za-z0-9_][A-Za-z0-9._]{2,29})(?![\w.])")

# URL path segments that are never usernames (language, static pages, ...).
_STOPWORDS = {
    "marketplace", "search", "item", "groups", "photo", "video", "watch",
    "profile", "people", "login", "share", "story", "reel", "reels", "post",
    "status", "home", "explore", "about", "help", "settings", "ad", "ads",
}


def resolve_binary(explicit: Optional[str] = None) -> Optional[str]:
    """Return a usable user-scanner binary path or None."""
    candidates = [
        explicit,
        os.environ.get("USER_SCANNER_BIN"),
        shutil.which("user-scanner"),
        DEFAULT_BIN,
    ]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def is_available(explicit: Optional[str] = None) -> bool:
    return resolve_binary(explicit) is not None


def extract_emails(text: str) -> List[str]:
    if not text:
        return []
    seen, out = set(), []
    for m in EMAIL_RE.findall(text):
        e = m.strip().lower().strip(".,;:)\"'")
        if e and e not in seen:
            seen.add(e)
            out.append(e)
    return out


def extract_usernames(text: str, url: str = "") -> List[str]:
    """Extract probable broker usernames/handles from text + listing URL."""
    blob = f"{text or ''}\n{url or ''}"
    found: List[str] = []
    seen = set()

    def _add(name: str):
        n = (name or "").strip().strip("@/ ")
        if not n or len(n) < 3 or len(n) > 40:
            return
        low = n.lower()
        if low in _STOPWORDS or low in seen:
            return
        # skip pure numbers that are likely ad ids, keep dubizzle ids out
        if n.isdigit():
            return
        seen.add(low)
        found.append(n)

    for _label, rx in SOCIAL_PATTERNS:
        for m in rx.findall(blob):
            _add(m.split("?")[0].split("/")[0])

    for m in HANDLE_RE.findall(blob):
        # avoid double-capturing the local part of emails
        _add(m)

    return found


def extract_contacts(text: str, url: str = "") -> Dict[str, List[str]]:
    return {
        "emails": extract_emails(text),
        "usernames": extract_usernames(text, url),
    }


def _run_cli(target_flag: str, target: str, modules: Optional[str],
             category: Optional[str], timeout: int,
             binary: Optional[str] = None, allow_loud: bool = False,
             cross_scan: bool = False) -> Dict[str, Any]:
    """Run `user-scanner -u/-e target -f json -o tmpfile` and parse hits.

    allow_loud includes modules that may notify the target (password-reset
    style checks) — off by default in user-scanner. cross_scan follows
    handles/links exposed by the first pass (email -> username pivots).
    """
    bin_path = resolve_binary(binary)
    if not bin_path:
        return {"ok": False, "error": "user-scanner binary not found. "
                "Set USER_SCANNER_BIN or install it (see README integration).",
                "target": target, "hits": [], "total_hits": 0}

    target = (target or "").strip()
    if not target:
        return {"ok": False, "error": "empty target", "target": target,
                "hits": [], "total_hits": 0}

    with tempfile.TemporaryDirectory(prefix="raven_osint_") as tmp:
        outfile = os.path.join(tmp, "out.json")
        cmd = [bin_path, target_flag, target, "-f", "json", "-o", outfile]
        if modules:
            cmd += ["-m", modules]
        if category:
            cmd += ["-c", category]
        if allow_loud:
            cmd += ["--allow-loud"]
        if cross_scan:
            cmd += ["--cross-scan"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"scan timed out after {timeout}s",
                    "target": target, "hits": [], "total_hits": 0}
        except Exception as e:
            return {"ok": False, "error": f"failed to run user-scanner: {e}",
                    "target": target, "hits": [], "total_hits": 0}

        try:
            with open(outfile, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return {"ok": False,
                    "error": f"no JSON output. stderr: {proc.stderr[-500:]}",
                    "target": target, "hits": [], "total_hits": 0}
        except Exception as e:
            return {"ok": False, "error": f"bad JSON output: {e}",
                    "target": target, "hits": [], "total_hits": 0}

    if isinstance(data, dict):
        data = [data]
    hits = [d for d in data
            if str(d.get("status", "")).lower() in ("found", "registered")]
    hits.sort(key=lambda d: str(d.get("site_name", "")))
    return {
        "ok": True,
        "target": target,
        "total_hits": len(hits),
        "total_checked": len(data),
        "hits": hits,
        "raw_stdout_tail": "",
    }


def scan_username(username: str, modules: Optional[str] = None,
                  category: Optional[str] = None, timeout: int = 180,
                  binary: Optional[str] = None, allow_loud: bool = False,
                  cross_scan: bool = False) -> Dict[str, Any]:
    """Scan one username. Keep modules narrow (e.g. 'github,instagram') for speed.

    Unlike email scans, username modules return REAL profile URLs
    (github.com/<user>), not homepages — use this to get profile links.
    """
    r = _run_cli("-u", username, modules, category, timeout, binary,
                 allow_loud=allow_loud, cross_scan=cross_scan)
    r["type"] = "username"
    return r


def scan_email(email: str, modules: Optional[str] = None,
               category: Optional[str] = None, timeout: int = 180,
               binary: Optional[str] = None, allow_loud: bool = False,
               cross_scan: bool = False) -> Dict[str, Any]:
    """Scan one email. Note: email modules only prove REGISTRATION — their
    `url` is the site homepage, not a profile link (the site never exposes
    the profile id to an unauthenticated check). Only Gravatar-style modules
    expose a real profile_url inside `extra`. To reach real profiles, run a
    username scan (or cross_scan) afterwards."""
    r = _run_cli("-e", email, modules, category, timeout, binary,
                 allow_loud=allow_loud, cross_scan=cross_scan)
    r["type"] = "email"
    return r


def guess_usernames_from_email(email: str) -> List[str]:
    """Derive probable usernames from an email local-part.

    john.doe99@gmail.com -> [john.doe99, johndoe99, john_doe99, ...].
    Scanning these as USERNAMES is what yields real profile URLs.
    """
    local = (email or "").split("@")[0].strip().lower()
    if not local or len(local) < 3:
        return []
    variants = [local]
    nosep = re.sub(r"[._-]+", "", local)
    if nosep != local and len(nosep) >= 3:
        variants.append(nosep)
    underscored = re.sub(r"[.-]+", "_", local)
    if underscored not in variants:
        variants.append(underscored)
    dashed = re.sub(r"[._]+", "-", local)
    if dashed not in variants and len(dashed) >= 3:
        variants.append(dashed)
    return variants[:4]


def extract_profile_link(hit: Dict[str, Any]) -> str:
    """Best-effort real profile link for one hit.

    Email hits only carry the site homepage in `url`; some (Gravatar)
    carry a true profile_url in `extra`. Username hits carry the real
    profile URL directly.
    """
    extra = hit.get("extra") or {}
    if isinstance(extra, dict):
        for key in ("profile_url", "profile", "profile_link", "link"):
            v = extra.get(key)
            if v and isinstance(v, str) and v.startswith("http"):
                return v
    return str(hit.get("url", "") or "")


def extra_summary(hit: Dict[str, Any]) -> str:
    """Compact human-readable summary of a hit's extra/metadata dict."""
    extra = hit.get("extra") or {}
    if not extra:
        media = hit.get("media") or {}
        if isinstance(media, dict) and media.get("avatar"):
            return "صورة بروفايل متاحة"
        return ""
    if isinstance(extra, dict):
        bits = []
        for k, v in list(extra.items())[:4]:
            vs = str(v)
            bits.append(f"{k}: {vs[:60]}")
        return "; ".join(bits)
    return str(extra)[:120]


def enrich_property(prop: Dict[str, Any], max_targets: int = 2,
                    modules: Optional[str] = "github,instagram,facebook",
                    timeout: int = 180, allow_loud: bool = False,
                    cross_scan: bool = False) -> Dict[str, Any]:
    """Extract contacts from one listing dict and scan up to max_targets.

    prop keys used: Title, Description, URL (same shape as SearchResult.to_dict()).
    Returns {"contacts": {...}, "scans": [scan_result, ...]}.
    """
    text = "\n".join([str(prop.get("Title", "") or ""),
                      str(prop.get("Description", "") or "")])
    url = str(prop.get("URL", "") or "")
    contacts = extract_contacts(text, url)

    targets: List[Dict[str, str]] = []
    for e in contacts["emails"][:max_targets]:
        targets.append({"type": "email", "value": e})
    remaining = max_targets - len(targets)
    for u in contacts["usernames"][:max(0, remaining)]:
        targets.append({"type": "username", "value": u})

    scans = []
    for t in targets:
        if t["type"] == "email":
            scans.append(scan_email(t["value"], modules=modules, timeout=timeout,
                                    allow_loud=allow_loud, cross_scan=cross_scan))
        else:
            scans.append(scan_username(t["value"], modules=modules, timeout=timeout,
                                       allow_loud=allow_loud, cross_scan=cross_scan))
    return {"contacts": contacts, "scans": scans}
