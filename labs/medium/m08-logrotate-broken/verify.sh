#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
L=/var/log/shopapp
R=/etc/logrotate.d/shopapp
ST=$LAB_STATE_DIR/m08-verify.state

if [[ ! -f $R ]]; then
    fail "$R is missing"
    finish_verify
fi

if logrotate -d "$R" 2>&1 | grep -qi 'error'; then
    fail "logrotate -d reports errors: $(logrotate -d "$R" 2>&1 | grep -i -m1 error)"
else
    pass "logrotate -d: no errors"
fi

sed 's/#.*//' "$R" | grep -qwE 'size|maxsize' && pass "rule rotates on size" || fail "rule has no size/maxsize - a burst can still fill the volume"

info "Forcing a rotation (logrotate -f) and sending traffic ..."
logrotate -f -s "$ST" "$R" >/dev/null 2>&1
sleep 1
before=$(stat -c %s "$L/app.log" 2>/dev/null || echo -1)
for _ in 1 2 3 4 5; do curl -s -o /dev/null --max-time 3 http://127.0.0.1/ || true; done
sleep 1
after=$(stat -c %s "$L/app.log" 2>/dev/null || echo -1)
[[ $after -gt $before && $before -ge 0 ]] && pass "app keeps writing to app.log after rotation" \
    || fail "app.log did not grow after rotation (where does the app write now? lsof -p \$(systemctl show -p MainPID --value shopapp))"

main=$(systemctl show -p MainPID --value shopapp)
if ls -l "/proc/$main/fd" 2>/dev/null | grep -q "$L/.*(deleted)"; then
    fail "shopapp still holds a deleted file in $L open"
else
    pass "no deleted log files held open by shopapp"
fi

use=$(df --output=pcent "$L" | tail -1 | tr -dc '0-9')
[[ $use -lt 50 ]] && pass "$L usage ${use}%" || fail "$L usage ${use}% (needs < 50%)"
[[ $(http_code http://127.0.0.1/health) == 200 ]] && pass "/health returns 200" || fail "/health is not 200"
rm -f "$ST"
finish_verify
