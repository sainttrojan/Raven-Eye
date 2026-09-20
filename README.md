# Raven-Eye (Real Estate OS)

Raven-Eye is a real estate operating system focused on the Egyptian market
(Madinaty and surroundings). It scrapes property listings from multiple
sources, filters them to Madinaty-only results, distinguishes private owners
from brokers, and enriches advertiser contact data with OSINT investigations
(phone numbers, emails, usernames). It ships with a Streamlit dashboard and
a 24/7 Telegram radar bot.

---

## Key Features

### 1. Multi-source scraping
- **Dubizzle direct scraping** — fetches listings from Dubizzle's internal
  endpoints, bypassing Google's limited index. Primary radar engine.
- **Google search scraping** — `site:`-scoped queries (PropertyFinder,
  Aqarmap, Facebook, Instagram, X/Twitter) with time filters.
- **Facebook Marketplace scraping** — authenticated Playwright session,
  card search plus optional item-page enrichment (description + phone).
  Requires a one-time manual login (`fb_login.py`).
- **Facebook Groups scraping** — searches configured real-estate groups and
  returns posts with the **author name and profile URL**, which Marketplace
  cards never expose.

### 2. Madinaty scoping (`core/listing_classifier.py`)
Search results leak in neighboring areas (El Shorouk, Badr, Rehab, Sarai,
Suez road, ...). The strict filter keeps only genuine Madinaty listings:
- Recognizes all spellings (madinaty variants, B-section and group numbers).
- Drops other-city mentions, including glued typos such as "الشروشقه".
- Drops proximity phrasing glued to Madinaty itself ("near Madinaty")
  while keeping inside references ("facing the club").
- Decodes percent-encoded URLs before matching so byte sequences cannot
  fake inside signals.

### 3. Owner vs broker classification (`core/listing_classifier.py`)
Point-based scoring over listing text, listing URL, post author name, and
phone-number frequency in the local database:
- Owner signals: "from owner", direct contact, no commission.
- Broker signals: office/company/marketing wording, agent page URLs,
  office names in the author field.
- Phone frequency is the strongest signal: one number behind 5+ saved
  listings is effectively never a private owner.
- Weak evidence returns `unknown` instead of guessing. Labels and scores
  are persisted per listing.

### 4. Phone OSINT (`core/phone_osint.py`, `core/phone_sites/`)
- Offline analysis via `phonenumbers`: validity, carrier
  (Vodafone/Orange/Etisalat/WE), region, line type. Instant, no network.
- Account checks via `ignorant`: whether the number is registered on
  Amazon, Instagram and Snapchat (does not alert the target).
- Pluggable website checks (`core/phone_sites/`): each site is one module
  exposing `NAME`, `DOMAIN` and `check()`. First module is Facebook
  account-recovery (E.164 plus national form, anonymous plus
  session-authenticated paths). New sites need no engine changes.
- Internal correlation: how many saved listings share the number, from
  which sources — the fastest broker detector in the system.
- Web footprint: quoted-number Google search through the project's own
  scraper (ScraperAPI credit applies), plus an optional per-site
  breakdown (facebook.com, dubizzle.com, olx, PropertyFinder, Aqarmap).
- Manual investigation deep links: WhatsApp, Telegram, Truecaller, Google.

### 5. Broker OSINT via user-scanner (`core/broker_osint.py`)
- Extracts emails and social handles from ad text and URLs.
- Runs `user-scanner` (~200 email modules / ~880 username modules):
  full scans, category/module scoping, `allow-loud` and `cross-scan`
  support.
- Derives probable usernames from email local-parts — username scans are
  what yield real profile URLs (email checks only prove registration).
- Results persisted in the database with profile-link and metadata columns.

### 6. Deep investigation (`core/deep_investigate.py`)
One call fans out across every engine for the identifiers at hand:
phone analysis plus email full scan plus username full scans (including
email-derived guesses), with a combined hit summary. Full scans take
several minutes.

### 7. Telegram radar bot (`radar_loop.py`, 24/7 background worker)
- Background loop over Madinaty queries with seen-URL memory (new
  listings only, no spam).
- Notifications carry price, area, owner/broker label, and the ad link.
- Commands: `/status`, `/pause`, `/resume`, `/restart`, `/credits`,
  `/search`, `/investigate` (username/email OSINT, fast or deep),
  `/checkphone` (phone OSINT, normal or with web search).
- Interactive buttons mirror the commands, including guided OSINT flows.

### 8. Streamlit dashboard (`app.py`, 7 tabs)
1. Live search — all sources, Madinaty-only toggle, owner/broker filter,
   Excel export.
2. Saved properties — database history with classification columns.
3. Settings — ZenRows key, ScraperAPI keys, Facebook session status,
   Facebook group list.
4. Broker investigation — username/email OSINT with profile links.
5. Phone investigation — number analysis, account checks, DB correlation,
   web footprint, per-site footprint.
6. Deep investigation — every identifier across every engine.
7. WhatsApp sender — see section 10.

### 9. Reports (`core/report_generator.py`)
OSINT results export to Excel and PDF, used by the Telegram bot flows.

### 10. WhatsApp sender (`core/wa_sender.py`, `wa_login.py`)
Sends text plus optional image from your own number through WhatsApp Web
(Playwright), with a subscriber list, Excel/CSV number import, random
inter-message delays, a per-run cap, and dry-run mode enabled by default.
- One-time login: `./venv/bin/python wa_login.py`, scan the QR, the
  script auto-saves once chats appear. The full browser profile
  (`wa_profile/`, IndexedDB included — the only persistence WhatsApp
  honors) is reused afterwards. The phone must stay online.
- Automation violates WhatsApp's terms and risks number bans: send only
  to consenting lists with generous delays.

### 11. Google Sheets lead sync (`core/sheets_sync.py`)
One-way sync of the local database to a single Google Sheet, split into
worksheets for distribution:
- **Sale / Rent / Other** — listings auto-classified from their text,
  each row with its save date (`Status` starts as `new`).
- **OSINT** — broker and phone investigation results.
- **WA Log** — every real WhatsApp send is logged automatically.
URLs already in the sheet are never duplicated, and sync only appends —
it never touches existing rows (assign leads freely).
- One-time setup: Google Cloud service-account JSON key, share the
  sheet with its `client_email` as Editor, then set the Sheet ID and
  key path in Settings tab (or `SHEET_ID` / `GOOGLE_CREDENTIALS_FILE`).
- Push listings and OSINT from the Saved tab after each run.

---

## Tech Stack
- Python 3.14, Streamlit, pandas, SQLite (local) / Supabase Postgres (online)
- Playwright + Chromium (Facebook sources)
- BeautifulSoup4, httpx, trio, psycopg (Postgres driver)
- pyTelegramBotAPI (bot), python-dotenv (config)
- External OSINT tools (cloned alongside this project):
  `user-scanner` (username/email), `ignorant` (phone accounts)
- Scraping engines: ZenRows (primary), ScraperAPI (Google footprint only)

---

## Project Structure
```
app.py                    Streamlit dashboard (7 tabs)
radar_loop.py             Telegram bot + background radar
fb_login.py               One-time Facebook manual login
wa_login.py               One-time WhatsApp QR login
main.py                   Minimal CLI scraping example
core/
  config.py               Keys, FB session + group list + sheet/DB URLs storage
  db.py                   SQLite local / Supabase Postgres online (auto-switch)
  parser.py               SmartParser (phone/price/area extraction)
  listing_classifier.py   Madinaty filter + owner/broker scorer
  broker_osint.py         user-scanner wrapper (email/username)
  phone_osint.py          phonenumbers + ignorant + correlation + footprint
  phone_sites/            Pluggable phone website checks (facebook first)
  deep_investigate.py     All engines, one call
  fb_session.py           Facebook browser lifecycle + entry points
  browser.py              Playwright context helpers
  wa_sender.py            WhatsApp Web sender + subscribers + sheet import
  report_generator.py     Excel/PDF OSINT reports
  sheets_sync.py          Google Sheets split sync (Sale/Rent/OSINT/WA Log)
scrapers/
  dubizzle.py             Dubizzle direct search
  google.py               Google site:-scoped search
  facebook.py             Marketplace search (+ optional page details)
  facebook_groups.py      Group search with post authors
models/result.py          SearchResult dataclass (incl. author fields)
start.sh                  Dual-process launcher (bot + dashboard)
migrate_to_supabase.py    One-shot SQLite -> Supabase copy
tests/                    Per-module test suites (run with project venv)
```

---

## Setup

### 1. Environment
```bash
cd Raven-Eye
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m playwright install chromium
```

### 2. External OSINT tools (expected paths)
```bash
# user-scanner (username/email) with its own venv, see its README
# ignorant (phone accounts) with its own venv, see its README
```
`core/broker_osint.py` resolves the `user-scanner` binary via the
`USER_SCANNER_BIN` env var, then `PATH`, then the default Desktop clone
path. `core/phone_osint.py` imports the `ignorant` library, which is also
listed in `requirements.txt`.

### 3. API keys
- `ZENROWS_API_KEY` — primary scraping engine (or paste in Settings tab).
- `SCRAPER_API_KEYS` — only needed for the phone web-footprint feature.
- Keys can also live in `config.json` (written by the Settings tab).

### 4. Facebook session (one time)
```bash
./venv/bin/python fb_login.py
```
Log in inside the opened browser window; the script saves the session
automatically once chats appear (`fb_storage_state.json`). Then add
your Madinaty groups (full URLs, one per line) in Settings tab, section
"Facebook groups". The account must be a member of private groups to
read them.

### 5. WhatsApp session (one time, for the sender tab)
```bash
./venv/bin/python wa_login.py
```
Scan the QR with your phone and wait — the script saves automatically
once chats appear (full browser profile in `wa_profile/`).

### 6. Run
```bash
bash start.sh
# bot runs in background, dashboard on http://localhost:8501
# start.sh prefers venv binaries and falls back to system ones
```

---

## Testing
Each integration has a suite runnable with the project venv:
```bash
./venv/bin/python -m tests.test_listing_classifier
./venv/bin/python -m tests.test_broker_osint
./venv/bin/python -m tests.test_phone_osint
./venv/bin/python -m tests.test_phone_sites
./venv/bin/python -m tests.test_deep_investigate
./venv/bin/python -m tests.test_facebook
./venv/bin/python -m tests.test_facebook_groups
./venv/bin/python -m tests.test_wa_sender
./venv/bin/python -m tests.test_db_backends
./venv/bin/python -m tests.test_sheets_sync
```
Live checks (ignorant, user-scanner single-module probes) are included;
they are passive existence checks and tolerate rate limits.

---

## Configuration reference
| Key | Source | Purpose |
| --- | --- | --- |
| `ZENROWS_API_KEY` | env / config.json / Settings | Primary scraping |
| `SCRAPER_API_KEYS` | env / config.json / Settings | Google web footprint |
| `FB_STORAGE_FILE` | env (default `fb_storage_state.json`) | FB session |
| `FB_GROUPS` | env / config.json / Settings | FB group list |
| `WA_PROFILE_DIR` | env (default `wa_profile/`) | WhatsApp session |
| `WA_SUBS_FILE` | env (default `wa_subscribers.json`) | WhatsApp subscribers |
| `DATABASE_URL` | Streamlit secrets / env / config.json / Settings | Supabase Postgres (empty = local SQLite) |
| `SHEET_ID` | env / config.json / Settings | Google Sheet for leads |
| `GOOGLE_CREDENTIALS_FILE` | env / config.json / Settings | Service-account JSON key |
| `USER_SCANNER_BIN` | env | user-scanner binary override |
| `TELEGRAM_TOKEN`, `ADMIN_CHAT_ID` | `radar_loop.py` / env | Bot wiring |

Local `raven_eye.db` holds listings (with owner labels and authors),
OSINT results, and phone checks. `seen_properties.json` holds radar memory.

## Online database (Supabase)

Streamlit Cloud wipes local files on every reboot, so the cloud
deployment uses Supabase Postgres while local runs keep SQLite — same
code, automatic switch via `DATABASE_URL`:

1. Create a free project at supabase.com, then copy the connection
   string (Project Settings > Database > Connection string, postgres
   user): `postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres`
2. Local: export it and copy existing data once:
   ```bash
   export DATABASE_URL="postgresql://..."
   venv/bin/python migrate_to_supabase.py
   ```
3. Streamlit Cloud: paste the same string as `DATABASE_URL` in the app
   Secrets (or in the Settings tab — Secrets survives reboots, the tab
   does not seed them).
4. Tables are created automatically with Row Level Security enabled and
   no public grants, so only this server-side code can reach them.

---

## Limitations (known, by design)
- Email OSINT proves registration only; profile URLs come from username
  scans, never from email checks (any tool has this property).
- Instagram's lookup endpoint can return false positives; the UI labels
  it as an indicator.
- Ignorant covers 3 sites and is rate-limit sensitive; the DB correlation
  and web footprint compensate.
- Facebook scraping depends on a valid logged-in session and group
  membership; re-run `fb_login.py` when the session expires.
- AI-assisted extraction and deal scoring are planned once an LLM API
  key is available; the `core/ai/` layer does not exist yet.

---

## Responsible use
Listings processed here are public advertisements. OSINT features are
provided for defensive research and purchase due diligence on the user's
own behalf. Do not use them to harass individuals, and respect each
platform's terms of service.
