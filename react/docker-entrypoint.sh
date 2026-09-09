#!/bin/sh
set -e

cat <<EOF > /usr/share/nginx/html/env-config.js
window.__ENV__ = {
  API_URL: "${API_URL:-http://localhost:8000}"
};
EOF

exec nginx -g 'daemon off;'
