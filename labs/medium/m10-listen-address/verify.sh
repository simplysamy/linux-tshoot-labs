#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

check "nginx -t passes" nginx -t

code=$(ip netns exec mon-ns curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://10.210.0.1/health 2>/dev/null)
[[ $code == 200 ]] && pass "probe (10.210.0.2) gets 200" || fail "probe gets '${code:-no answer}'"

[[ $(http_code http://127.0.0.1/) == 200 ]] && pass "localhost still works" || fail "localhost is broken now"

if ss -Hltn 'sport = :80' | awk '{print $4}' | grep -qE '^(0\.0\.0\.0|\*|\[::\]):80$'; then
    pass "nginx listens on all addresses"
else
    warn "nginx listens only on: $(ss -Hltn 'sport = :80' | awk '{print $4}' | xargs) - fine if intended"
fi

if iptables -S INPUT | grep -q 'SEC-118'; then
    pass "SEC-118 rule kept (narrowed with an exception)"
else
    warn "SEC-118 rule removed - OK only if security agreed it was a mistake"
fi
finish_verify
