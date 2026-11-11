#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
S=$LAB_STATE_DIR

[[ -f $S/h03-server.pid ]] && kill "$(cat "$S/h03-server.pid")" 2>/dev/null || true
for ns in app-ns client-ns; do
    for pid in $(ip netns pids "$ns" 2>/dev/null); do kill "$pid" 2>/dev/null || true; done
    ip netns del "$ns" 2>/dev/null || true
done
ip link del h-cl 2>/dev/null || true
ip link del h-ap 2>/dev/null || true

while iptables -S FORWARD | grep -q 'SEC-204'; do
    rule=$(iptables -S FORWARD | grep 'SEC-204' | head -1 | sed 's/^-A /-D /')
    eval "iptables $rule"
done
# remove ACCEPT exceptions students may have added for port 9000 / these subnets
while rule=$(iptables -S FORWARD | grep -E '10\.20[01]\.0\.|dport 9000' | head -1) && [[ -n $rule ]]; do
    eval "iptables ${rule/-A /-D }"
done

if [[ -f $S/h03-ip_forward.orig ]]; then
    sysctl -qw net.ipv4.ip_forward="$(cat "$S/h03-ip_forward.orig")"
fi
rm -rf "$S/h03-www" "$S/h03-server.pid" "$S/h03-ip_forward.orig"
info "Note: if you created a sysctl.d file for ip_forward, it is left in place."
restore_baseline
