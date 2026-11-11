#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
D=/srv/shopdata

iuse=$(df --output=ipcent "$D" | tail -1 | tr -dc '0-9')
[[ $iuse -lt 50 ]] && pass "inode usage on $D is ${iuse}% (< 50%)" || fail "inode usage on $D is ${iuse}% (needs < 50%)"

live=$(find "$D/sessions" -type f -name 'sess_live_*' 2>/dev/null | wc -l)
[[ $live -ge 40 ]] && pass "all 40 live sessions kept" || fail "only $live of 40 live sessions left - you deleted active customer sessions!"

[[ $(http_code http://127.0.0.1/health) == 200 ]] && pass "/health returns 200" || fail "/health is not 200"

if grep -Eq '^[[:space:]]*[^#[:space:]].*find /srv/shopdata/sessions' /etc/cron.d/shopapp-session-cleanup 2>/dev/null; then
    pass "session cleanup cron is enabled again"
else
    fail "session cleanup cron is still disabled - this will happen again"
fi
finish_verify
