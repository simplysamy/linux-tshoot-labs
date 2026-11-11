#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

if grep -q '10.255.255.53' /etc/resolv.conf 2>/dev/null; then
    fail "/etc/resolv.conf still points at the dead resolver 10.255.255.53"
else
    pass "dead resolver removed from /etc/resolv.conf"
fi

check "ubuntu.com resolves (getent ahosts ubuntu.com)" timeout 10 getent ahosts ubuntu.com

if grep -Eq '^[^#]*203\.0\.113\.77' /etc/hosts; then
    fail "stale example.com entry still active in /etc/hosts"
else
    pass "no stale example.com entry in /etc/hosts"
fi

ip=$(timeout 10 getent hosts example.com | awk '{print $1; exit}')
if [[ -n $ip && $ip != 203.0.113.77 ]]; then pass "example.com resolves to $ip"; else fail "example.com does not resolve correctly (got '${ip:-nothing}')"; fi

check "HTTPS to example.com works" curl -fsS -o /dev/null --max-time 10 https://example.com/
finish_verify
