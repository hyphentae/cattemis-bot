#!/bin/sh
set -e

WEB_URL="http://web:8080"
TUNNEL_FILE="/tunnel/url.txt"
TUNNEL_TMP="${TUNNEL_FILE}.tmp"

# The named volume survives container restarts. Remove the previous quick
# tunnel URL before Docker can report this container as healthy.
rm -f "$TUNNEL_FILE" "$TUNNEL_TMP"

sleep 2

echo "[cloudflared] starting tunnel to $WEB_URL"

cloudflared tunnel --url "$WEB_URL" --no-autoupdate 2>&1 | while IFS= read -r line; do
  echo "$line"
  if echo "$line" | grep -qE 'https://[a-z0-9-]+\.trycloudflare\.com'; then
    url=$(echo "$line" | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com')
    echo "[cloudflared] tunnel URL: $url"
    echo "$url" > "$TUNNEL_TMP"
    mv "$TUNNEL_TMP" "$TUNNEL_FILE"
  fi
done
