"""Facebook Groups scraper (authenticated session required).

Needs the same one-time login as Marketplace: `venv/bin/python fb_login.py`.
The account must be a MEMBER of private groups to read them.

For each configured group it searches the group for the query and returns
posts as SearchResult items — including the AUTHOR name + profile URL,
which Marketplace cards never expose (gold for owner/broker distinction).
"""

import re
from typing import Dict, List, Optional
from urllib.parse import quote, urlparse

from scrapers.base import BaseScraper
from models.result import SearchResult
from core.parser import SmartParser

FB_HOME = "https://www.facebook.com"

# hrefs that look like posts (relative or absolute).
POST_RE = re.compile(r"(/(?:groups/[^/]+/)?posts/\d+|/permalink/|story\.php\?story_fbid=|/reel/|/watch\?v=)")

# single-segment profile hrefs (/name/, /profile.php?id=...) — NOT these.
_NON_PROFILE = {
    "groups", "posts", "marketplace", "hashtag", "pages", "events",
    "watch", "reel", "reels", "stories", "story.php", "photo.php",
    "video.php", "permalink", "search", "help", "settings", "login",
    "policies", "privacy", "about", "ads", "business", "gaming",
}


def group_token(group_url_or_id: str) -> str:
    """Accept a group URL or raw id/slug, return the path token for search."""
    s = (group_url_or_id or "").strip().strip("/")
    if not s:
        return ""
    if "facebook.com" in s:
        m = re.search(r"/groups/([^/?#]+)", s)
        return m.group(1) if m else ""
    return s.split("/")[-1].split("?")[0]


def group_search_url(token: str, query: str) -> str:
    return f"{FB_HOME}/groups/{token}/search/?query={quote(query)}"


def normalize_post_url(href: str) -> Optional[str]:
    """Canonical absolute post URL, or None if not a post link."""
    if not href:
        return None
    h = href.split("?")[0].rstrip("/") or "/"
    if not POST_RE.search(h):
        return None
    if h.startswith("http"):
        return h
    return FB_HOME + (h if h.startswith("/") else "/" + h)


def is_profile_href(href: str) -> bool:
    """True for user-profile hrefs (/name/, /profile.php?id=..., /user/x)."""
    if not href:
        return False
    h = href.split("?")[0].strip("/")
    if h.startswith("http"):
        try:
            h = urlparse(h).path.strip("/")
        except Exception:
            return False
    if h in ("profile.php",) or h.startswith("profile.php"):
        return True
    if h.startswith("user/"):
        return True
    if "/" in h or not h:
        return False
    return h.lower() not in _NON_PROFILE


def absolutize(href: str) -> str:
    if href.startswith("http"):
        return href.split("?")[0]
    return FB_HOME + (href if href.startswith("/") else "/" + href)


def build_result(item: Dict[str, str], group_label: str) -> Optional[SearchResult]:
    """Pure dict->SearchResult builder (unit-testable).

    item: {post_url, author_name, author_url, text, time}
    """
    post_url = normalize_post_url(item.get("post_url", "") or "")
    if not post_url:
        return None
    text = re.sub(r"\s+", " ", (item.get("text") or "")).strip()
    if not text:
        return None
    parsed = SmartParser.parse_text(text)
    title = text[:140] + ("..." if len(text) > 140 else "")
    author_url = item.get("author_url") or ""
    return SearchResult(
        source=f"Facebook Group ({group_label})",
        title=title,
        url=post_url,
        price=parsed.get("price"),
        area=parsed.get("area"),
        phone_number=parsed.get("phone_number"),
        description=text[:2000],
        author=item.get("author_name") or None,
        author_url=absolutize(author_url) if author_url and is_profile_href(author_url) else None,
    )


_ARTICLE_JS = """() => {
  const out = [];
  const STOP = new Set(%s);
  const arts = document.querySelectorAll('div[role="article"]');
  arts.forEach(a => {
    const postA = a.querySelector('a[href*="/posts/"]');
    if (!postA) return;
    let author = null, authorUrl = null;
    const links = a.querySelectorAll('a[href]');
    for (const l of links) {
      let h = l.getAttribute('href') || '';
      const hq = h.split('?')[0].replace(/^\\/+|\\/+$/g, '');
      if (hq === 'profile.php' || hq.startsWith('user/')) {
        author = (l.innerText || '').trim(); authorUrl = h; break;
      }
      if (!hq || hq.includes('/') || STOP.has(hq.toLowerCase())) continue;
      const t = (l.innerText || '').trim();
      if (t && t.length < 80) { author = t; authorUrl = h; break; }
    }
    let time = '';
    const ab = a.querySelector('abbr');
    if (ab) time = (ab.innerText || '').trim();
    out.push({post_url: postA.getAttribute('href') || '',
              author_name: author, author_url: authorUrl,
              text: (a.innerText || '').slice(0, 2000), time: time});
  });
  return out;
}""" % (repr(sorted(_NON_PROFILE)),)


class FacebookGroupsScraper(BaseScraper):
    def __init__(self, page=None):
        super().__init__(page)

    async def search_group(self, group: str, query: str,
                           max_pages: int = 3) -> List[SearchResult]:
        """Search one group (URL, id or slug) for the query."""
        if self.page is None:
            raise RuntimeError("FacebookGroupsScraper needs an authenticated page "
                               "(use core.fb_session.run_facebook_groups_search).")
        token = group_token(group)
        if not token:
            return []
        results: List[SearchResult] = []
        seen = set()
        try:
            await self.page.goto(group_search_url(token, query),
                                 wait_until="domcontentloaded")
            await self.page.wait_for_timeout(4000)
            scrolls = max(2, min(int(max_pages) * 2, 12))
            for _ in range(scrolls):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.page.wait_for_timeout(2000)
                try:
                    items = await self.page.evaluate(_ARTICLE_JS)
                except Exception:
                    continue
                for it in items or []:
                    try:
                        card = build_result(it, token)
                        if card and card.url not in seen:
                            seen.add(card.url)
                            results.append(card)
                    except Exception:
                        continue
        except Exception as e:
            print(f"Failed to search Facebook group {token}: {e}")
        return results

    async def search(self, query: str, time_filter: str = "",
                     max_pages: int = 3) -> List[SearchResult]:
        return await self.search_groups([], query, max_pages=max_pages)

    async def search_groups(self, groups: List[str], query: str,
                            max_pages: int = 3) -> List[SearchResult]:
        all_results: List[SearchResult] = []
        seen = set()
        for g in groups or []:
            for r in await self.search_group(g, query, max_pages=max_pages):
                if r.url not in seen:
                    seen.add(r.url)
                    all_results.append(r)
        return all_results
