#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
C=/etc/report-builder.conf

check "report-builder is active" systemctl is-active --quiet report-builder

getconf() { sed 's/#.*//' "$C" | awk -F= -v k="$1" '{gsub(/[[:space:]]/,"")} $1==k{print $2}'; }
w=$(getconf workers); mb=$(getconf worker_mb)
total_mb=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
if [[ $w =~ ^[0-9]+$ && $mb =~ ^[0-9]+$ && $w -ge 1 && $(( w * mb )) -le $(( total_mb / 2 )) ]]; then
    pass "report-builder needs $((w*mb)) MB (<= 50% of ${total_mb} MB RAM)"
else
    fail "report-builder config workers=$w x ${mb} MB does not fit in 50% of ${total_mb} MB RAM"
fi

sw=$(sysctl -n vm.swappiness)
[[ $sw -le 60 ]] && pass "vm.swappiness=$sw at runtime" || fail "vm.swappiness=$sw at runtime"
if grep -hsE '^[[:space:]]*vm\.swappiness' /etc/sysctl.conf /etc/sysctl.d/*.conf \
        | sed 's/#.*//' | awk -F= '{gsub(/[[:space:]]/,"",$2); if ($2 > 60) bad=1} END{exit !bad}'; then
    fail "a file in /etc/sysctl.d or /etc/sysctl.conf still sets swappiness > 60 (comes back at reboot)"
else
    pass "no persisted swappiness > 60"
fi

[[ -z $(swapon --noheadings --show) ]] && warn "swap is off - OK for the lab, but understand what that means under pressure"

info "Measuring swap activity for 6 seconds ..."
io=$(vmstat 1 7 | tail -n 6 | awk '{s += $7 + $8} END{print int(s/6)}')
[[ $io -lt 50 ]] && pass "swap in+out average ${io} KB/s" || fail "still swapping: ${io} KB/s (si+so)"
finish_verify
