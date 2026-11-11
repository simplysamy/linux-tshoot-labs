#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

if grep -Eq '^[[:space:]]*trace_requests[[:space:]]*=[[:space:]]*true' /etc/shopapp/config.ini; then
    fail "request tracing is still on (it leaks one fd per request)"
else
    pass "request tracing is off"
fi

pid=$(systemctl show -p MainPID --value shopapp)
if [[ -z $pid || $pid == 0 ]]; then
    fail "shopapp is not running"
    finish_verify
fi

soft=$(awk '/Max open files/{print $4}' "/proc/$pid/limits")
if [[ $soft == unlimited || $soft -ge 1024 ]]; then pass "shopapp soft NOFILE limit is $soft (>= 1024)"; else fail "shopapp soft NOFILE limit is $soft (needs >= 1024)"; fi

info "Sending 300 requests..."
for _ in $(seq 300); do curl -s -o /dev/null --max-time 2 http://127.0.0.1:8080/ || true; done
nfd=$(ls "/proc/$pid/fd" | wc -l)
[[ $nfd -lt 50 ]] && pass "shopapp has $nfd open fds after 300 requests (no leak)" || fail "shopapp has $nfd open fds after 300 requests - still leaking"

[[ $(http_code http://127.0.0.1/health) == 200 ]] && pass "/health via nginx returns 200" || fail "/health via nginx is not 200"
finish_verify
