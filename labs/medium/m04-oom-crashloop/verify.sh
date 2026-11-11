#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

max=$(awk -F= '/^[[:space:]]*max_mb/{gsub(/[[:space:]]/,"",$2); print $2}' /etc/cache-warmer.conf)
if [[ -n $max && $max -gt 0 && $max -le 120 ]]; then
    pass "cache max_mb=$max is bounded and below the 160M MemoryMax"
else
    fail "cache max_mb='${max}' - must be > 0 and well below MemoryMax (160M)"
fi

lim=$(systemctl show -p MemoryMax --value cache-warmer)
if [[ $lim == infinity ]]; then
    fail "MemoryMax was removed - the limit protects the host. Fix the config, keep the limit"
else
    pass "MemoryMax still set ($lim bytes)"
fi

check "cache-warmer is active" systemctl is-active --quiet cache-warmer

info "Watching for restarts for 20 seconds..."
r1=$(systemctl show -p NRestarts --value cache-warmer)
sleep 20
r2=$(systemctl show -p NRestarts --value cache-warmer)
[[ $r1 == "$r2" ]] && pass "no restarts in 20s (NRestarts=$r2)" || fail "service restarted $((r2 - r1)) time(s) in 20s"

mem=$(systemctl show -p MemoryCurrent --value cache-warmer)
[[ $mem =~ ^[0-9]+$ ]] && info "current memory: $((mem / 1048576)) MB"
finish_verify
