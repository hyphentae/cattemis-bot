#!/bin/sh
set -e

WEB_URL="http://web:8080"
TUNNEL_FILE="/tunnel/url.txt"

echo "[cloudflared] starting tunnel to $WEB_URL"

# запускаем cloudflared и парсим URL из stderr
cloudflared tunnel --url "$WEB_URL" --no-autoupdate 2>&1 | while IFS= read -r line; do
  echo "$line"
  if echo "$line" | grep -qE 'https://[a-z0-9-]+\.trycloudflare\.com'; then
    url=$(echo "$line" | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com')
    echo "[cloudflared] tunnel URL: $url"
    echo "$url" > "$TUNNEL_FILE"
  fi
done
