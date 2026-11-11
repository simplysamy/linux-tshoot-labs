#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

max=$(sysctl -n net.netfilter.nf_conntrack_max 2>/dev/null || echo 0)
[[ $max -ge 16384 ]] && pass "nf_conntrack_max=$max" || fail "nf_conntrack_max=$max (needs >= 16384)"

low=$(grep -hsE '^[[:space:]]*net\.(netfilter\.)?nf_conntrack_max' /etc/sysctl.conf /etc/sysctl.d/*.conf /run/sysctl.d/*.conf \
      | sed 's/#.*//; s/.*=//; s/[[:space:]]//g' | awk '$1 < 16384' | head -1)
[[ -z $low ]] && pass "no low conntrack limit persisted" || fail "a sysctl file still sets nf_conntrack_max=$low (comes back at reboot)"

check "metrics-scraper is active" systemctl is-active --quiet metrics-scraper
check "metrics-exporter is active" systemctl is-active --quiet metrics-exporter
pool=$(awk -F= '/^[[:space:]]*pool_size/{gsub(/[[:space:]]/,"",$2); sub(/;.*/,"",$2); print $2}' /etc/metrics-scraper.conf)
[[ $pool =~ ^[0-9]+$ && $pool -le 50 ]] && pass "scraper pool_size=$pool" || fail "scraper pool_size=$pool - still a connection hog"

est=$(ss -Htn state established '( dport = :9100 )' | wc -l)
[[ $est -le 60 ]] && pass "$est connections to the exporter" || fail "$est open connections to the exporter"

count=$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo 0)
[[ $count -lt $(( max / 2 )) ]] && pass "conntrack table ${count}/${max}" || fail "conntrack table ${count}/${max}"

check "SEC-099 rule still in place" bash -c "iptables -S INPUT | grep -q SEC-099"

slow=0
for _ in $(seq 30); do
    t=$(curl -s -o /dev/null -w '%{http_code} %{time_connect}' --max-time 3 http://127.0.0.1/ 2>/dev/null)
    [[ ${t%% *} == 200 ]] && awk -v x="${t#* }" 'BEGIN{exit !(x < 0.5)}' || slow=$((slow+1))
done
[[ $slow -eq 0 ]] && pass "30/30 new connections fast and OK" || fail "$slow/30 connections slow or failed"

if journalctl -k --since "-30s" --no-pager -q 2>/dev/null | grep -q 'table full'; then
    fail "kernel still logs 'table full' (last 30s)"
else
    pass "no 'table full' in the kernel log (last 30s)"
fi
finish_verify
