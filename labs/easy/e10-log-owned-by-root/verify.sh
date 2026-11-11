#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
L=/var/log/shopapp

u=$(systemctl show -p User --value shopapp)
[[ $u == shopapp ]] && pass "service runs as user shopapp" || fail "service User='$u' - it must run as shopapp"

[[ $(stat -c %U "$L/app.log" 2>/dev/null) == shopapp ]] && pass "app.log owned by shopapp" || fail "app.log not owned by shopapp"
m=$(stat -c %a "$L/app.log" 2>/dev/null)
(( (8#${m:-0} & 8#002) == 0 )) && pass "app.log is not world-writable" || fail "app.log is world-writable ($m)"
m=$(stat -c %a "$L")
(( (8#$m & 8#002) == 0 )) && pass "$L is not world-writable" || fail "$L is world-writable ($m)"

check "shopapp is active" systemctl is-active --quiet shopapp
r1=$(systemctl show -p NRestarts --value shopapp); sleep 5
r2=$(systemctl show -p NRestarts --value shopapp)
[[ $r1 == "$r2" ]] && pass "no restarts in 5s" || fail "shopapp is still restarting"
[[ $(http_code http://127.0.0.1/health) == 200 ]] && pass "/health returns 200" || fail "/health is not 200"
finish_verify
