#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

# 1. The approved batch job must be untouched.
check "batch-encoder (approved job) is still running" systemctl is-active --quiet batch-encoder
nice=$(ps -o ni= -p "$(systemctl show -p MainPID --value batch-encoder)" 2>/dev/null | tr -d ' ')
[[ $nice == 19 ]] && pass "batch-encoder still at nice 19" || fail "batch-encoder nice is '${nice:-?}' (should stay 19)"

# 2. The IO hog must be gone or constrained.
limited_cfg() {
    systemctl cat audit-sync.service 2>/dev/null | grep -Eq '^[[:space:]]*(IOSchedulingClass=(idle|3)|IOWeight=([1-9]|[1-4][0-9]|50)$|IOWriteBandwidthMax=|IOWriteIOPSMax=)'
}

pids=$(pgrep -f 'of=/var/tmp/audit-sync.dat' || true)
if [[ -z $pids ]]; then
    pass "audit-sync IO load is not running right now"
elif limited_cfg; then
    pass "audit-sync is running but IO-limited by its unit config"
else
    fail "audit-sync is hammering the disk with sync writes (PIDs: $(echo $pids))"
fi

if systemctl is-active --quiet audit-sync.timer && ! limited_cfg; then
    fail "audit-sync.timer is still active and the service has no IO limits - it will be back in 20s"
else
    pass "audit-sync will not come back unconstrained"
fi

info "iowait sample (5s):"
vmstat 1 5 | awk 'NR==1||NR==2||NR>3'
finish_verify
