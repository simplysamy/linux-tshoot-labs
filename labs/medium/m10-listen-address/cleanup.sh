#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
for pid in $(ip netns pids mon-ns 2>/dev/null); do kill "$pid" 2>/dev/null || true; done
ip netns del mon-ns 2>/dev/null || true
ip link del h-mon 2>/dev/null || true
# remove the SEC-118 rule and any rule students added for this subnet
while rule=$(iptables -S INPUT | grep -E 'SEC-118|10\.210\.0\.|INC-2010' | head -1) && [[ -n $rule ]]; do
    eval "iptables ${rule/-A /-D }"
done
restore_baseline     # reinstalls the nginx site
