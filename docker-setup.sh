#!/bin/bash
# First-time Docker setup: creates ./data with empty placeholder files,
# then builds and starts everything.
cd "$(dirname "$0")"
mkdir -p data/wa_profile
for f in raven_eye.db config.json fb_storage_state.json fb_cookies.json \
         wa_storage_state.json wa_subscribers.json seen_properties.json \
         subscribers.json; do
    [ -e "data/$f" ] || touch "data/$f"
done
echo "Copy your existing files into ./data if you have them, e.g.:"
echo "  cp raven_eye.db config.json wa_profile -r data/  (wa_profile: cp -r wa_profile data/)"
echo ""
echo "Then run:  docker compose up -d --build"
echo "Dashboard: http://localhost:8501"
