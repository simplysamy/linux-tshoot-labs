#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

owner=$(ss -Hltnp 'sport = :80' | grep -o 'users:(("[^"]*' | head -1 | sed 's/users:(("//')
[[ $owner == nginx ]] && pass "port 80 is owned by nginx" || fail "port 80 is owned by '${owner:-nobody}', expected nginx"

check "nginx is active" systemctl is-active --quiet nginx
if systemctl is-enabled --quiet legacy-status 2>/dev/null; then
    fail "legacy-status is still enabled - it will steal port 80 again after reboot"
else
    pass "legacy-status will not start at boot"
fi
if systemctl is-active --quiet legacy-status 2>/dev/null; then fail "legacy-status is still running"; else pass "legacy-status is stopped"; fi

body=$(curl -s --max-time 5 http://127.0.0.1/)
[[ $body == *"shopapp is running"* ]] && pass "http://localhost/ serves shopapp" || fail "http://localhost/ does not serve shopapp"
finish_verify
