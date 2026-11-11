#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
R=/srv/backups/shop-report.txt

if systemctl start shopapp-report.service 2>/dev/null; then
    pass "shopapp-report.service runs successfully"
else
    fail "shopapp-report.service fails: $(systemctl show -p ExecMainStatus --value shopapp-report) (see journalctl -u shopapp-report)"
fi

age=$(( $(date +%s) - $(stat -c %Y "$R" 2>/dev/null || echo 0) ))
[[ $age -lt 60 ]] && pass "report is fresh (${age}s old)" || fail "report is ${age}s old"
grep -q '^sessions=' "$R" 2>/dev/null && pass "report contains shopctl stats" || fail "report has no stats from shopctl"

check "shopapp-report.timer is enabled" systemctl is-enabled --quiet shopapp-report.timer
check "shopapp-report.timer is active"  systemctl is-active --quiet shopapp-report.timer
finish_verify
