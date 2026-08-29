# Raven Eye Real Estate Search System

Raven Eye is a professional, advanced data aggregation and scraping system designed specifically for the real estate market. The core objective of this project is to scrape, aggregate, and organize direct-from-owner real estate listings across various search engines and listing platforms into a centralized, clean, and ad-free dashboard.

---

## Project Overview & Features

### 1. Robust Search Engine Integration
- **Google Search Scraper:** A highly accurate scraping module utilizing ScraperAPI to bypass Google's anti-scraping measures. It retrieves the latest organic search results matching complex real estate queries.
- **Advanced Query Filtering:** Users can refine their searches via the dashboard using the following parameters:
  - **Time of Publication:** Filter listings by Any Time, Past 24 Hours, Past Week, or Past Month.
  - **Target Domains:** Restrict searches to specific leading real estate platforms (e.g., PropertyFinder, Dubizzle, Aqarmap) or search the entire web.
  - **Exact Match Validation:** Enforce strict exact-match queries to filter out irrelevant listings.

### 2. User Interface (Dashboard)
- **Framework:** The frontend is built using Streamlit to provide a highly interactive web application.
- **Corporate Design:** Features a professional, minimalist aesthetic using a Dark Mode base (Charcoal Gray) with subtle Champagne Gold accents, designed specifically for enterprise and management presentations.
- **Data Export:** All aggregated data (Title, URL, Source, Description) is dynamically structured into a Pandas DataFrame and can be exported instantly to an Arabic-supported, cleanly formatted Microsoft Excel (.xlsx) file.

---

## The Facebook Marketplace Challenge (Technical Documentation)

During the development of Raven Eye, integration with Facebook Marketplace was heavily tested. However, Facebook employs highly aggressive Anti-Bot and scraping protection systems which presented significant technical challenges:

1. **Automated Browser Detection:** Initial attempts to scrape using standard headless Playwright instances were immediately flagged by Facebook, trapping the automation in an infinite loading loop.
2. **Advanced CAPTCHA Systems:** We integrated the playwright-stealth library to mask the browser's automation flags. While this successfully bypassed the infinite loading screen, it triggered a strict Arkose Labs human verification challenge (CAPTCHA).
3. **Session Hijacking Attempts:** We attempted to bypass the login phase entirely by extracting the user's active session cookies directly from their open Google Chrome browser using the rowser-cookie3 library. However, Chrome places a strict database lock on its session files while running. Bypassing this lock required either shutting down the browser entirely during extraction or escalating the script to full Administrator privileges, both of which severely degraded the user experience.

**Current Status:** The Facebook scraping module has been temporarily disabled and excluded from the main execution pipeline to ensure the core system remains highly stable. Future iterations of Raven Eye will address this by utilizing pre-warmed accounts, residential proxies, or more advanced headless browser evasion techniques.

---

## Installation & Setup Guide

Raven Eye is built using Python. Below are the steps to deploy and run the system on both Windows and Linux environments.

### Prerequisites
- Python 3.9 or higher.
- Git.
- pip or uv package manager.

### 1. Clone the Repository
`ash
git clone https://github.com/your-username/Raven-Eye.git
cd Raven-Eye
`

### 2. Install Dependencies

**For Windows / Linux:**
`ash
pip install -r requirements.txt
`

### 3. Environment Configuration
Ensure you have your ScraperAPI key ready. The system requires this key to execute searches without being blocked by search engines.

### 4. Running the Application

**Option A: Running the Web Dashboard (Recommended)**
To launch the interactive Streamlit dashboard:

**Windows:**
`powershell
python -m streamlit run app.py
`
*(If using the uv package manager locally as configured during development, use: .\uv_extracted\uv.exe run streamlit run app.py)*

**Linux / macOS:**
`ash
streamlit run app.py
`

**Option B: Running the Command-Line Script**
To run the scraper without the web interface and directly generate the Excel file:

**Windows / Linux:**
`ash
python main.py
`

---

## Architecture
- pp.py: The main entry point for the Streamlit web dashboard.
- main.py: The CLI alternative for running headless scraping jobs.
- scrapers/google.py: The core scraping logic bridging queries to ScraperAPI.
- .streamlit/config.toml: Contains the corporate UI theme configurations.
