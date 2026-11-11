#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

check "traffic-replay is active" systemctl is-active --quiet traffic-replay
check "shopapp is active" systemctl is-active --quiet shopapp

# quota as "usec of CPU per second": infinity or a number with unit (e.g. 50ms, 1s)
quota_ok() {   # unit -> true if no quota or quota >= 50% of one CPU
    local q; q=$(systemctl show -p CPUQuotaPerSecUSec --value "$1" 2>/dev/null)
    [[ -z $q || $q == infinity ]] && return 0
    local us
    case $q in
        *ms) us=$(( ${q%ms} * 1000 )) ;;
        *us) us=${q%us} ;;
        *s)  us=$(awk -v v="${q%s}" 'BEGIN{print int(v*1000000)}') ;;
        *)   return 1 ;;
    esac
    [[ $us -ge 500000 ]]
}

quota_ok shopapp && pass "shopapp has no tight CPU quota" \
    || fail "shopapp CPUQuota is $(systemctl show -p CPUQuotaPerSecUSec --value shopapp)/s"

slice=$(systemctl show -p Slice --value shopapp)
if quota_ok "$slice"; then
    pass "parent slice $slice has no tight CPU quota"
else
    fail "parent slice $slice is capped at $(systemctl show -p CPUQuotaPerSecUSec --value "$slice")/s"
fi

cg=/sys/fs/cgroup$(systemctl show -p ControlGroup --value shopapp)
if [[ -f $cg/cpu.stat ]]; then
    t1=$(awk '/^nr_throttled/{print $2}' "$cg/cpu.stat"); sleep 5
    t2=$(awk '/^nr_throttled/{print $2}' "$cg/cpu.stat")
    [[ $(( t2 - t1 )) -le 2 ]] && pass "no throttling in 5s (nr_throttled +$((t2-t1)))" \
        || fail "still throttled: nr_throttled +$((t2-t1)) in 5s"
fi

sum=0; max=0; n=20
for _ in $(seq $n); do
    t=$(curl -s -o /dev/null -w '%{time_total}' --max-time 5 http://127.0.0.1/ 2>/dev/null || echo 5)
    ms=$(awk -v t="$t" 'BEGIN{print int(t*1000)}')
    sum=$((sum + ms)); [[ $ms -gt $max ]] && max=$ms
done
avg=$((sum / n))
[[ $avg -lt 200 && $max -lt 1000 ]] && pass "latency avg ${avg} ms, max ${max} ms" \
    || fail "latency avg ${avg} ms, max ${max} ms (need avg < 200, max < 1000)"
finish_verify
