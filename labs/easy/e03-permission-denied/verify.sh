#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

check "user shopapp can enter /etc/shopapp" sudo -u shopapp test -x /etc/shopapp
check "user shopapp can read config.ini" sudo -u shopapp test -r /etc/shopapp/config.ini

mode=$(stat -c %a /etc/shopapp/config.ini)
other=${mode: -1}
if (( other & 4 )); then
    fail "config.ini is world-readable (mode $mode) - the hardening goal was to block other users"
else
    pass "config.ini is not world-readable (mode $mode)"
fi
if sudo -u shopapp test -w /etc/shopapp/config.ini; then
    fail "shopapp can WRITE its own config - give it read only"
else
    pass "shopapp cannot modify its config"
fi

check "shopapp service is active" systemctl is-active --quiet shopapp
[[ $(http_code http://127.0.0.1/health) == 200 ]] && pass "/health returns 200" || fail "/health is not 200"
finish_verify
