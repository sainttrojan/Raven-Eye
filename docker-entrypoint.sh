#!/bin/bash
# Ensure bind-mounted data files exist (empty) so Docker doesn't
# create directories in their place. Never truncates existing files.
mkdir -p /app/data 2>/dev/null || true
for f in raven_eye.db config.json fb_storage_state.json fb_cookies.json \
         wa_storage_state.json wa_subscribers.json seen_properties.json \
         subscribers.json; do
    [ -e "/app/$f" ] || touch "/app/$f"
done
mkdir -p /app/wa_profile /app/.streamlit
exec "$@"
