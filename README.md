# Raven Eye System 🦅

A powerful Real Estate Intelligence System built with Python, Streamlit, and ScraperAPI.
It acts as a smart engine to find, extract, and monitor real estate listings from top platforms in Egypt (Dubizzle, Property Finder, Aqarmap, Facebook, Instagram, Twitter).

## Features ✨
- **Live Search & Extraction:** Search properties using advanced Google Dorks.
- **Smart URL Filtering:** Strictly ignores category/search pages and targets exact individual listings.
- **API Key Rotation:** Supports multiple ScraperAPI keys and automatically rotates them on failure or exhaustion (403/429).
- **Persistent Database:** SQLite integration to save history and avoid duplicate entries.
- **Export to Excel:** Download live reports and historical data.

## Installation 🛠️
```bash
# Clone the repository
git clone https://github.com/sainttrojan/Raven-Eye.git
cd Raven-Eye

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the system
streamlit run app.py
```

## Configuration ⚙️
1. Go to the "الإعدادات" (Settings) tab inside the app.
2. Enter your ScraperAPI keys (one per line).
3. The system will save them securely to `config.json` and automatically handle key rotation.

## Next Features Roadmap 🗺️
- Deep Scraping: Extract full descriptions and images from inside listing pages.
- Owner vs Broker Detection: AI/Heuristic filtering to classify posters.
- Analytics Dashboard.
- Live Alerts via Telegram/WhatsApp.
