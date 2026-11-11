#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

st=$(systemctl is-enabled shopapp 2>/dev/null)
[[ $st == enabled ]] && pass "shopapp is enabled" || fail "shopapp is-enabled: $st"

if [[ -L /etc/systemd/system/multi-user.target.wants/shopapp.service ]]; then
    pass "shopapp is wanted by multi-user.target"
else
    fail "no multi-user.target.wants/shopapp.service link - it will not start at boot"
fi

if systemctl cat shopapp 2>/dev/null | grep -qE '^WantedBy=.*multi-user\.target'; then
    pass "unit declares WantedBy=multi-user.target"
else
    fail "unit has no [Install] WantedBy=multi-user.target (hand-made symlinks don't count)"
fi

check "shopapp is active" systemctl is-active --quiet shopapp
[[ $(http_code http://127.0.0.1/health) == 200 ]] && pass "/health returns 200" || fail "/health is not 200"
finish_verify
