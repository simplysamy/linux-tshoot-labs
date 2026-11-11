#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
L=/var/log/shopapp

use=$(df --output=pcent "$L" | tail -1 | tr -dc '0-9')
if [[ $use -lt 80 ]]; then pass "$L usage is ${use}% (< 80%)"; else fail "$L usage is ${use}% (needs < 80%)"; fi

if [[ -f $L/debug-trace.log ]]; then
    sz=$(stat -c %s "$L/debug-trace.log")
    if [[ $sz -gt 10485760 ]]; then fail "debug-trace.log is still $((sz/1048576))MB"; else pass "debug-trace.log is small"; fi
else
    pass "debug-trace.log removed"
fi

before=$(stat -c %s "$L/app.log" 2>/dev/null || echo 0)
curl -s -o /dev/null --max-time 3 http://127.0.0.1/ || true
sleep 1
after=$(stat -c %s "$L/app.log" 2>/dev/null || echo 0)
if [[ $after -gt $before ]]; then pass "shopapp is writing to app.log again"; else fail "shopapp is not writing new lines to app.log"; fi

[[ $(http_code http://127.0.0.1/health) == 200 ]] && pass "/health returns 200" || fail "/health is not 200"
finish_verify
