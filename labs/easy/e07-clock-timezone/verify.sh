#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

tz=$(timedatectl show -p Timezone --value)
[[ $tz == Etc/UTC || $tz == UTC ]] && pass "timezone is $tz" || fail "timezone is $tz (should be UTC)"

[[ $(timedatectl show -p NTP --value) == yes ]] && pass "NTP sync enabled" || fail "NTP sync is disabled"

if systemctl is-active --quiet systemd-timesyncd || systemctl is-active --quiet chrony || systemctl is-active --quiet chronyd; then
    pass "time sync service is running"
else
    fail "no time sync service running (systemd-timesyncd / chrony)"
fi

if [[ $(timedatectl show -p NTPSynchronized --value) == yes ]]; then
    pass "clock is synchronised"
else
    warn "clock not synchronised yet (needs network access to an NTP server - not counted)"
fi

curl -s -o /dev/null --max-time 3 http://127.0.0.1/ || true
sleep 1
ts=$(tail -n1 /var/log/shopapp/app.log | cut -c1-19)
if logged=$(date -u -d "$ts" +%s 2>/dev/null); then
    diff=$(( $(date -u +%s) - logged )); diff=${diff#-}
    [[ $diff -lt 120 ]] && pass "app.log timestamps are UTC ($ts)" \
        || fail "app.log last line '$ts' is ${diff}s away from UTC now - did the app pick up the change?"
else
    fail "cannot read a timestamp from app.log"
fi
finish_verify
