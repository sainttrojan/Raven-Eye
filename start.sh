#!/bin/bash
cd "$(dirname "$0")"
# Prefer the project venv (has ignorant, phonenumbers, dotenv, ...).
# Fall back to system python/streamlit (e.g. Render containers without venv/).
PY="python"
ST="streamlit"
if [ -x "venv/bin/python" ]; then PY="venv/bin/python"; fi
if [ -x "venv/bin/streamlit" ]; then ST="venv/bin/streamlit"; fi
# Start the radar loop in the background
$PY radar_loop.py &
# Start the Streamlit app
$ST run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0
