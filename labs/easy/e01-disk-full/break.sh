#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

L=/var/log/shopapp
mkdir -p "$L/archive"
for i in 1 2 3 4 5; do
    fallocate -l 6M "$L/archive/app.log.$i"
done

# A "temporary" debug trace someone left enabled. It fills the volume.
yes "$(date '+%F %T') DEBUG cart-svc trace_id=7f3a9c payload={\"items\":[{\"sku\":\"A-1001\",\"qty\":1}]} upstream=pricing latency_ms=12" \
    > "$L/debug-trace.log" 2>/dev/null || true
chown -R shopapp:shopapp "$L"
sync

# Generate traffic so the app tries (and fails) to log.
for _ in $(seq 5); do curl -s -o /dev/null --max-time 3 http://127.0.0.1/ || true; done
