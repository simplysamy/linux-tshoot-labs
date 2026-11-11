#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

if pgrep -f /usr/local/bin/shopapp-reindex >/dev/null; then
    fail "shopapp-reindex is running: PIDs $(pgrep -d, -f /usr/local/bin/shopapp-reindex)"
else
    pass "no shopapp-reindex process"
fi

if grep -Eqs '^[[:space:]]*[^#[:space:]].*shopapp-reindex' /etc/cron.d/shopapp-reindex /etc/crontab /var/spool/cron/crontabs/*; then
    fail "a cron entry still launches shopapp-reindex - it will be back within a minute"
else
    pass "no active cron entry launches shopapp-reindex"
fi

load1=$(cut -d' ' -f1 /proc/loadavg)
info "current 1-min load average: $load1 (it decays slowly - give it a few minutes)"
[[ $(http_code http://127.0.0.1/health) == 200 ]] && pass "/health returns 200" || fail "/health is not 200"
finish_verify
