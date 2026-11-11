#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
M=/mnt/reports

# count tasks that have been in D state and alive for > 10 s (short disk waits are normal)
d=$(ps -eo stat=,etimes= | awk '$1 ~ /^D/ && $2 > 10' | wc -l)
[[ $d -eq 0 ]] && pass "no stuck D-state processes" || fail "$d processes stuck in D state (ps -eo pid,stat,wchan:32,cmd | awk '\$2 ~ /D/')"

timeout -s KILL 5 df -h >/dev/null 2>&1 && pass "df -h returns" || fail "df -h hangs"

if findmnt -n "$M" >/dev/null; then
    pass "$M is mounted"
    if timeout -s KILL 5 ls "$M" >/dev/null 2>&1; then pass "ls $M returns"; else fail "ls $M hangs"; fi
    t=$M/.verify-$$
    if timeout -s KILL 5 bash -c "echo ok > $t && rm -f $t" 2>/dev/null; then pass "$M is writable"; else fail "$M is not writable"; fi
else
    fail "$M is not mounted"
fi

if timeout -s KILL 15 /usr/local/bin/report-export 2>/dev/null; then
    pass "report-export works"
else
    fail "report-export fails or hangs"
fi

opts=$(awk '$2=="/mnt/reports"{print $4}' /etc/fstab)
[[ ,$opts, == *,_netdev,* ]] && pass "fstab has _netdev" || fail "fstab entry lacks _netdev (opts: $opts)"
[[ ,$opts, == *,nofail,* ]] && pass "fstab has nofail" || fail "fstab entry lacks nofail - a dead NAS blocks boot"
[[ ,$opts, == *,soft,* ]] && warn "soft mount: no more hangs, but writes can fail silently - know the trade-off"

if iptables -S OUTPUT | grep -q 'SEC-410' && ! timeout 3 bash -c '</dev/tcp/10.240.0.10/2049' 2>/dev/null; then
    fail "NFS to the NAS (10.240.0.10:2049) is still blocked"
else
    pass "NAS reachable on tcp/2049"
fi
finish_verify
