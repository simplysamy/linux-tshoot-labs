#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

check "nginx configuration test passes (nginx -t)" nginx -t
check "nginx service is active" systemctl is-active --quiet nginx
check "nginx is enabled at boot" systemctl is-enabled --quiet nginx
[[ $(http_code http://127.0.0.1/) == 200 ]] && pass "http://localhost/ returns 200" || fail "http://localhost/ does not return 200"
if grep -Eq 'proxy_read_timeout[[:space:]]+30s;' /etc/nginx/sites-available/shopapp; then
    pass "the colleague's intended 30s timeout is kept"
else
    warn "the 30s proxy_read_timeout change was dropped - fine for now, but tell the colleague"
fi
finish_verify
