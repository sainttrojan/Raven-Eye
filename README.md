# 🦅 Raven-Eye (Real Estate OS)

Raven-Eye is an advanced, intelligent Real Estate Operating System designed to disrupt the traditional property search in the Egyptian market. It acts as an automated radar that bypasses broker manipulations, duplicate advertisements, and restricted search engines to source properties **directly from owners** on Dubizzle.

---

## 🚀 Key Features

### 1. Direct & Deep Scraping (Dubizzle)
- Completely bypasses Google's limited index by fetching data directly from Dubizzle's internal servers.
- Uses **ScraperAPI (`render=true`)** to successfully bypass Cloudflare protections and JavaScript challenges.
- Intelligently parses React-based dynamic HTML structures (extracting from `<li aria-label="Listing">` tags).

### 2. High-Performance Multithreading
- Capable of fetching and analyzing up to **200 pages concurrently**.
- Built-in `ThreadPoolExecutor` ensures blazing-fast extraction without exceeding ScraperAPI's free-tier concurrency limits (Max 5 concurrent threads).
- URL encoding logic dynamically replaces spaces with dashes to match Dubizzle's strictly formatted query URLs.

### 3. Telegram Radar Bot (24/7 Background Worker)
A fully integrated, interactive Telegram bot that acts as your personal real estate assistant in your pocket.
- **Automated Radar:** Runs a background loop every 3 hours to fetch new properties.
- **Smart Memory:** Keeps track of previously seen URLs to ensure you only get notified about **brand new** listings, preventing spam.
- **Interactive Commands:**
  - `/status` : Check if the background radar is running.
  - `/pause` / `/resume` : Start or pause the automated background scraping.
  - `/credits` : Instantly check your remaining ScraperAPI balance.
  - `/search <query>` : Manually trigger an immediate deep-search and get results pushed directly to Telegram.

### 4. Advanced OSINT Capabilities
- **Phone Number Profiling:** Validates and checks phone numbers against major platforms (Amazon, Instagram, Snapchat) using `ignorant` and `phonenumbers`.
- **Digital Footprint:** Searches for phone number appearances across the web and cross-references with previously seen properties in the internal database.
- **Broker Investigation:** Scans usernames and emails across various platforms (GitHub, Instagram, Facebook) using `user-scanner`.
- **Telegram Integrations:** Added `/investigate` and `/checkphone` commands for quick on-the-go analysis.

### 5. Dual-Process Deployment (Render)
- Includes a custom `start.sh` script that spins up **both** the interactive Telegram background bot and the Streamlit web dashboard simultaneously within the same container.
- Fully compatible with Render Web Services and easily integrated with Custom Domains (e.g., Namecheap).

---

## 🛠️ Tech Stack
- **Python 3.x**
- **Streamlit:** Interactive web dashboard for manual searches and visual data analysis.
- **BeautifulSoup4:** Advanced DOM parsing.
- **pyTelegramBotAPI:** For the interactive Telegram bot interface.
- **Concurrent.futures:** For asynchronous multithreaded scraping.

---

## 💻 How to Run Locally

1. Clone the repository.
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your environment variables (or add them directly in `radar_loop.py` & `.streamlit/secrets.toml`):
   - `SCRAPER_API_KEY`
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Run the dual-process startup script:
   ```bash
   bash start.sh
   ```
   *(This will launch the Telegram bot in the background and start the Streamlit web server on port 8501).*

---

*Built with 💻 for the Egyptian Real Estate Market.*
