#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
S=$LAB_STATE_DIR
[[ -f $S/h07-server.pid ]] && kill "$(cat "$S/h07-server.pid")" 2>/dev/null || true
for ns in cust-ns vpn-ns dc-ns; do
    for pid in $(ip netns pids "$ns" 2>/dev/null); do kill "$pid" 2>/dev/null || true; done
    ip netns del "$ns" 2>/dev/null || true      # deleting a namespace removes its veths and iptables rules
done
rm -rf "$S/h07-www" "$S/h07-server.pid"
restore_baseline
