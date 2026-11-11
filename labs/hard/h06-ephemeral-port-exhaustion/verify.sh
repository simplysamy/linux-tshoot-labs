#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

read -r lo hi < <(sysctl -n net.ipv4.ip_local_port_range)
[[ $(( hi - lo )) -ge 10000 ]] && pass "ip_local_port_range $lo-$hi ($((hi-lo+1)) ports)" \
    || fail "ip_local_port_range $lo-$hi is only $((hi-lo+1)) ports"

narrow=$(grep -hsE '^[[:space:]]*net\.ipv4\.ip_local_port_range' /etc/sysctl.conf /etc/sysctl.d/*.conf /run/sysctl.d/*.conf \
         | sed 's/#.*//; s/.*=//' | awk '$2-$1 < 10000' | head -1)
[[ -z $narrow ]] && pass "no narrow port range persisted in sysctl files" \
    || fail "a sysctl file still sets ip_local_port_range = $narrow (comes back at reboot)"

check "price-sync is active" systemctl is-active --quiet price-sync
reuse=$(awk -F= '/^[[:space:]]*reuse_connections/{gsub(/[[:space:]]/,"",$2); print tolower($2)}' /etc/price-sync.conf)
[[ $reuse =~ ^(true|yes|on|1)$ ]] && pass "price-sync reuses connections" || fail "price-sync still opens a new connection per request"

info "Waiting 10s, then sending 30 requests ..."
sleep 10
bad=0
for _ in $(seq 30); do [[ $(http_code http://127.0.0.1/) == 200 ]] || bad=$((bad+1)); done
[[ $bad -eq 0 ]] && pass "30/30 requests returned 200" || fail "$bad/30 requests failed"

tw=$(ss -Htan state time-wait | wc -l)
[[ $tw -lt 1000 ]] && pass "TIME_WAIT sockets: $tw" || fail "TIME_WAIT sockets: $tw"

if journalctl -u price-sync --since "-10s" --no-pager -q | grep -q 'ERROR'; then
    fail "price-sync reported errors in the last 10s"
else
    pass "price-sync: no errors in the last 10s"
fi
finish_verify
