#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

check "inventory-api is listening inside app-ns" sh -c "ip netns exec app-ns ss -Hltn 'sport = :9000' | grep -q 9000"

body=$(ip netns exec client-ns curl -s --max-time 4 http://10.200.0.2:9000/ 2>/dev/null)
[[ $body == *"inventory-api OK"* ]] && pass "client-ns -> http://10.200.0.2:9000 works" || fail "client-ns cannot reach http://10.200.0.2:9000"

if grep -rhsE '^[[:space:]]*net\.ipv4\.ip_forward[[:space:]]*=[[:space:]]*1' /etc/sysctl.conf /etc/sysctl.d/ >/dev/null; then
    pass "ip_forward=1 is persistent (survives reboot)"
else
    fail "ip_forward is not persisted in /etc/sysctl.conf or /etc/sysctl.d/ - a reboot breaks it again"
fi

if iptables -S FORWARD | grep -q 'SEC-204'; then
    if [[ $body == *"inventory-api OK"* ]]; then
        warn "SEC-204 DROP rule still present but bypassed - make sure security agrees with an ACCEPT exception"
    fi
else
    pass "SEC-204 rule removed/replaced (document it in the ticket and tell the security team)"
fi
finish_verify
