# Raven Eye Real Estate Search System

Raven Eye is a professional, advanced data aggregation and scraping system designed specifically for the real estate market. The core objective of this project is to scrape, aggregate, and organize direct-from-owner real estate listings across various search engines, listing platforms, and social media into a centralized, clean, and ad-free dashboard.

---

## Project Overview & Features

### 1. Robust Search Engine Integration
- **Google Search Scraper:** A highly accurate scraping module utilizing ScraperAPI to bypass Google's anti-scraping measures. It retrieves the latest organic search results matching complex real estate queries.
- **Deep Pagination:** The system can automatically paginate through Google search results (up to 10 pages), extracting a massive amount of data per query.
- **Advanced Query Filtering:** Users can refine their searches via the dashboard using the following parameters:
  - **Time of Publication:** Filter listings by Any Time, Past 24 Hours, Past Week, or Past Month.
  - **Target Domains & Social Media:** Restrict searches to specific real estate platforms (e.g., PropertyFinder, Dubizzle, Aqarmap) or search social media platforms (Facebook, Instagram, Twitter) bypassing their anti-bot measures using Google Dorks.
  - **Exact Match Validation:** Enforce strict exact-match queries to filter out irrelevant listings.

### 2. Smart Data Parsing (NLP/Regex)
- Automatically parses and extracts critical data directly from search snippets:
  - **Phone Numbers:** Detects Egyptian mobile numbers with various formatting (e.g., 010, +2011).
  - **Prices:** Extracts numeric values tagged with currencies (EGP, جنيه, مليون).
  - **Area/Size:** Detects property sizes (e.g., 120م, 150 sqm).

### 3. Database & Storage
- **SQLite Integration:** All scraped properties are automatically stored in a local SQLite database (`raven_eye.db`).
- **Deduplication:** The system prevents saving identical listings by utilizing URL-based uniqueness checks.
- **History Tracking:** Users can view their entire search history directly from the dashboard and export the cumulative dataset.

### 4. User Interface (Dashboard)
- **Framework:** The frontend is built using Streamlit to provide a highly interactive web application.
- **Corporate Design:** Features a professional, minimalist aesthetic using a Dark Mode base (Charcoal Gray) with subtle Champagne Gold accents.
- **Data Export:** All aggregated data (Title, Price, Area, Phone, URL, Source, Description) is dynamically structured into a Pandas DataFrame and can be exported instantly to an Arabic-supported, cleanly formatted Microsoft Excel (.xlsx) file.

---

## The Facebook Marketplace Challenge (Technical Documentation)

During the development of Raven Eye, integration with Facebook Marketplace was heavily tested. Facebook employs highly aggressive Anti-Bot systems:
1. **Automated Browser Detection:** Initial attempts to scrape using standard headless Playwright instances were immediately flagged.
2. **Advanced CAPTCHA Systems:** Bypassing detection triggered Arkose Labs human verification challenges (CAPTCHA).

**Current Status:** Direct Facebook scraping has been temporarily disabled. **Instead, the system successfully utilizes Google Dorks (`site:facebook.com`) to extract indexed public Facebook posts and groups without triggering any CAPTCHA or Login walls.**

---

## Installation & Setup Guide

Raven Eye is built using Python. Below are the steps to deploy and run the system.

### Prerequisites
- Python 3.9 or higher.
- Git.

### 1. Clone the Repository
```bash
git clone https://github.com/sainttrojan/Raven-Eye.git
cd Raven-Eye
```

### 2. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install openpyxl
```

### 3. Running the Application

**Option A: Running the Web Dashboard (Recommended)**
```bash
streamlit run app.py
```

**Option B: Running the Command-Line Script**
To run the scraper without the web interface and save directly to the database:
```bash
python main.py
```

---

## Architecture
- `app.py`: The main entry point for the Streamlit web dashboard.
- `main.py`: The CLI alternative for running headless scraping jobs.
- `scrapers/google.py`: The core scraping logic bridging queries to ScraperAPI with pagination support.
- `core/parser.py`: The Smart Parser utilizing Regex for data extraction.
- `core/db.py`: SQLite Database Manager for persistent storage.
