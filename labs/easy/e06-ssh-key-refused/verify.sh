#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
K=$LAB_STATE_DIR/e06

if ssh -i "$K/deploy_key" -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
       -o ConnectTimeout=5 deploy@127.0.0.1 true 2>/dev/null; then
    pass "key login as deploy works"
else
    fail "key login as deploy still refused"
fi

nowrite() {   # path -> true if not writable by group/other
    local m; m=$(stat -c %a "$1" 2>/dev/null) || return 1
    (( (8#$m & 8#022) == 0 ))
}
check "/home/deploy is not group/world writable" nowrite /home/deploy
m=$(stat -c %a /home/deploy/.ssh 2>/dev/null)
[[ $m == 700 ]] && pass "~/.ssh is 700" || fail "~/.ssh is $m (should be 700)"
m=$(stat -c %a /home/deploy/.ssh/authorized_keys 2>/dev/null)
[[ $m == 600 || $m == 644 || $m == 640 ]] && pass "authorized_keys is $m" || fail "authorized_keys is $m (should be 600)"
[[ $(stat -c %U /home/deploy/.ssh/authorized_keys 2>/dev/null) == deploy ]] \
    && pass "authorized_keys owned by deploy" || fail "authorized_keys not owned by deploy"

if sshd -T 2>/dev/null | grep -qi '^strictmodes yes'; then
    pass "sshd still enforces StrictModes"
else
    fail "StrictModes was turned off - that weakens every account. Revert it"
fi
finish_verify
