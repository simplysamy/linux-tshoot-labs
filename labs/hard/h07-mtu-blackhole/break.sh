#!/usr/bin/env bash
# [cust-ns] cl0 10.230.1.2/24 (mtu 1500) --- r0 10.230.1.1 (mtu 1400, "tunnel") [vpn-ns] r1 10.230.2.1 --- ap0 10.230.2.2 [dc-ns]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

S=$LAB_STATE_DIR
for ns in cust-ns vpn-ns dc-ns; do ip netns del "$ns" 2>/dev/null || true; done
for ns in cust-ns vpn-ns dc-ns; do ip netns add "$ns"; ip -n "$ns" link set lo up; done

ip link add cl0 netns cust-ns type veth peer name r0 netns vpn-ns
ip link add r1  netns vpn-ns  type veth peer name ap0 netns dc-ns

ip -n cust-ns addr add 10.230.1.2/24 dev cl0
ip -n cust-ns link set cl0 up
ip -n cust-ns route add default via 10.230.1.1

ip -n vpn-ns addr add 10.230.1.1/24 dev r0
ip -n vpn-ns addr add 10.230.2.1/24 dev r1
ip -n vpn-ns link set r0 mtu 1400          # the provider's tunnel
ip -n vpn-ns link set r0 up
ip -n vpn-ns link set r1 up
ip netns exec vpn-ns sysctl -qw net.ipv4.ip_forward=1

ip -n dc-ns addr add 10.230.2.2/24 dev ap0
ip -n dc-ns link set ap0 up
ip -n dc-ns route add default via 10.230.2.1

# SEC-311: the gateway must not send any ICMP
ip netns exec vpn-ns iptables -A OUTPUT -p icmp -m comment --comment "SEC-311 no ICMP from VPN gateway" -j DROP

# catalogue service
W=$S/h07-www
rm -rf "$W"; mkdir -p "$W"
echo "catalog-api OK" > "$W/small.txt"
head -c 500000 /dev/urandom > "$W/catalog.bin"
ip netns exec dc-ns setsid nohup python3 -m http.server 8000 --bind 10.230.2.2 --directory "$W" \
    >/dev/null 2>&1 < /dev/null &
echo $! > "$S/h07-server.pid"
sleep 1
