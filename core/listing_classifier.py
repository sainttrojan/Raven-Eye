"""Madinaty scoping + owner/broker classification for listings.

Two independent questions Raven-Eye must answer per listing:
  1. Is it really in Madinaty? (Google/Dubizzle results leak in El Shorouk,
     Badr, Rehab, Tagamoa, ...). See is_madinaty().
  2. Is the advertiser the real owner or a broker? Scoring over text
     signals + listing URL + phone-frequency in our own DB. See classify().

Phone frequency is the strongest broker signal: a number behind 5+
saved listings is almost never a private owner selling one flat.
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

# ---------- text normalization ----------

_ALEF_RE = re.compile(r"[أإآ]")
_TASHKEEL_RE = re.compile(r"[\u064B-\u0652\u0670]")


def _norm(text: str) -> str:
    t = _TASHKEEL_RE.sub("", text or "")
    t = _ALEF_RE.sub("ا", t)
    t = t.replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    return t.lower()


# ---------- Madinaty scoping ----------

MADINATY_MARKERS = ["مدينتي", "madinaty", "madinty", "madenaty"]

# Other cities/compounds whose ads leak into "Madinaty" searches.
OTHER_CITIES = [
    "الشروق", "الشرو", "بدر", "الرحاب", "العبور", "التجمع", "العاصمه", "العاصمة الاداريه",
    "المستقبل", "هليوبوليس", "زايد", "اكتوبر", "القاهره الجديده", "مصر الجديده",
    "المعادي", "نصر", "القطاميه", "السخنه", "العين السخنه", "مراسي", "الساحل",
    "السويس", "طريق السويس", "سراي", "سراى", "لافيستا", "حسن علام",
    "التراث", "العاصمة",
    "shorouk", "rehab", "tagamoa", "new cairo", "zayed", "october",
    "suez", "sarai", "lavista", "la vista",
]

# "الشرو" prefix catches concatenated typos like "الشروشقه" (الشروق+شقه
# glued without space) seen in real Dubizzle titles.

_OTHER_NORM = [_norm(c) for c in OTHER_CITIES]

# Proximity phrasing ("near/in front of Madinaty") means the unit is
# OUTSIDE Madinaty — but ONLY when glued to Madinaty itself
# ("بالقرب من مدينتي"). "امام النادي" alone is usually inside.
_PROX_BEFORE_RE = re.compile(
    r"(بالقرب من|قريب\w* من|امام|جنب|بجوار|دقيقت\w*|دقائق من|سور بسور)"
    r"\W{0,15}مدينت"
)


def _has_proximity(blob_norm: str) -> Optional[str]:
    m = _PROX_BEFORE_RE.search(blob_norm)
    return m.group(1) if m else None


# Inside-Madinaty proof: B-section numbers (B8/B14/...) and group numbers
# override proximity phrasing when both appear.
_INSIDE_RE = re.compile(
    r"\bb\s?\d{1,3}\b|بى\s?\d{1,3}|بي\s?\d{1,3}|مجموعه\s?\d+|all seasons",
)


def is_madinaty(title: str = "", description: str = "", url: str = "",
                strict: bool = True) -> Dict[str, Any]:
    """Decide whether a listing is really in Madinaty.

    strict=True: requires a Madinaty mention, no other-city mention, and
    no outside-proximity phrasing (without inside proof like B8/مجموعة).
    strict=False: a Madinaty mention alone is enough.
    """
    # URLs come percent-encoded from Dubizzle (%D9%85...) — decode first so
    # %XX byte sequences can't fake inside-signals like "b9".
    url = unquote(url or "")
    blob = _norm(f"{title}\n{description}\n{url}")
    mentions = [m for m in MADINATY_MARKERS if _norm(m) in blob]
    other = next((c for c, n in zip(OTHER_CITIES, _OTHER_NORM) if n in blob), None)
    if not mentions:
        return {"in_madinaty": False, "mentions": mentions, "other_city": other,
                "reason": "لا يوجد ذكر لمدينتي"}
    if not strict:
        return {"in_madinaty": True, "mentions": mentions, "other_city": other,
                "reason": ""}
    if other:
        return {"in_madinaty": False, "mentions": mentions, "other_city": other,
                "reason": f"يذكر مدينة أخرى: {other}"}
    prox = _has_proximity(blob)
    if prox and not _INSIDE_RE.search(blob):
        return {"in_madinaty": False, "mentions": mentions, "other_city": other,
                "reason": f"صيغة قرب/جوار ({prox}) بدون إثبات داخلي — خارج مدينتي"}
    return {"in_madinaty": True, "mentions": mentions, "other_city": other,
            "reason": ""}


# ---------- owner vs broker ----------

OWNER_PATTERNS = [
    (r"من المالك", "يذكر (من المالك)"),
    (r"المالك مباشر\w*", "يذكر التواصل مع المالك مباشرة"),
    (r"بدون وسيط", "يذكر (بدون وسيط)"),
    (r"بدون عمول\w*", "يذكر (بدون عمولة)"),
    (r"بدون سمس", "يذكر (بدون سمسرة)"),
    (r"مالك اول|اول مالك|يد اولي|يد أولي", "يذكر أنه أول مالك"),
    (r"\bowner\b|from owner|by owner|no agent|no commission|direct from landlord",
     "يذكر المالك بالإنجليزية"),
]

BROKER_PATTERNS = [
    (r"مكتب", "يذكر (مكتب)"),
    (r"شرك\w*", "يذكر (شركة)"),
    (r"تسويق", "يذكر (تسويق)"),
    (r"وسيط", "يذكر (وسيط)"),
    (r"بروكر|broker|brokers", "يذكر (بروكر)"),
    (r"سمسا?ر", "يذكر (سمسار)"),
    (r"عمول\w*", "يذكر (عمولة)"),
    (r"لدينا|متوفر لدينا|متاح لدينا|عروضنا|لدينا عروض", "صيغة جمع/مخزون (لدينا...)"),
    (r"agency|agencies|\brealtor\b", "يذكر وكالة بالإنجليزية"),
]

URL_BROKER_RE = re.compile(r"/agent/|/broker/|/compan|/agenc", re.I)

# Phone-frequency thresholds over saved listings sharing the number.
BROKER_PHONE_MIN = 5   # >=5 listings -> strong broker signal
LEAN_PHONE_MIN = 2     # 2-4 listings -> weak broker signal


def classify(title: str = "", description: str = "", url: str = "",
             phone_listing_count: Optional[int] = None,
             scraper_broker_type: Optional[str] = None,
             author: str = "") -> Dict[str, Any]:
    """Score a listing. Returns label owner|broker|unknown + reasons.

    phone_listing_count: how many saved listings share the advertiser's
    number (use core.phone_osint.find_in_database). None = skip signal.
    author: post author name (Facebook groups) — office/company names
    in it are a strong broker signal.
    """
    url = unquote(url or "")
    blob = _norm(f"{title}\n{description}")
    owner_pts, broker_pts = 0, 0
    reasons: List[str] = []

    for pat, reason in OWNER_PATTERNS:
        if re.search(pat, blob):
            owner_pts += 2
            reasons.append("مالك: " + reason)
    for pat, reason in BROKER_PATTERNS:
        if re.search(pat, blob):
            broker_pts += 2
            reasons.append("بروكر: " + reason)
    if url and URL_BROKER_RE.search(url):
        broker_pts += 3
        reasons.append("بروكر: رابط صفحة وكيل/شركة")

    if author:
        ablob = _norm(author)
        for pat, reason in BROKER_PATTERNS:
            if re.search(pat, ablob):
                broker_pts += 3
                reasons.append("بروكر: اسم المعلن (" + author.strip() + ")")
                break

    if scraper_broker_type:
        s = scraper_broker_type.strip().lower()
        if s in ("broker", "agent", "company", "سمسار", "وسيط", "مكتب", "شركة"):
            broker_pts += 3
            reasons.append("بروكر: تصنيف المصدر")
        elif s in ("owner", "مالك", "المالك"):
            owner_pts += 3
            reasons.append("مالك: تصنيف المصدر")

    if phone_listing_count is not None:
        if phone_listing_count >= BROKER_PHONE_MIN:
            broker_pts += 3
            reasons.append(f"بروكر: نفس الرقم في {phone_listing_count} إعلانات")
        elif phone_listing_count >= LEAN_PHONE_MIN:
            broker_pts += 1
            reasons.append(f"احتمال بروكر: نفس الرقم في {phone_listing_count} إعلانات")
        elif phone_listing_count == 1:
            owner_pts += 1
            reasons.append("مالك محتمل: الرقم ظهر في إعلان واحد فقط")

    if broker_pts >= 3 and broker_pts > owner_pts:
        label = "broker"
    elif owner_pts >= 2 and owner_pts > broker_pts:
        label = "owner"
    else:
        label = "unknown"
    return {"label": label,
            "label_ar": {"owner": "مالك", "broker": "بروكر",
                         "unknown": "غير معروف"}[label],
            "owner_score": owner_pts, "broker_score": broker_pts,
            "reasons": reasons}
