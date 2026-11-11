#!/usr/bin/env bash
# Topology (network namespaces act as separate machines, the VM is the router):
#
#  [client-ns]  cl0 10.201.0.2/24 ---- h-cl 10.201.0.1/24  [ VM / router ]  h-ap 10.200.0.1/24 ---- ap0 10.200.0.2/24  [app-ns]
#                                                                                                         inventory-api :9000
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

S=$LAB_STATE_DIR
sysctl -n net.ipv4.ip_forward > "$S/h03-ip_forward.orig"

ip netns del client-ns 2>/dev/null || true
ip netns del app-ns 2>/dev/null || true
ip netns add client-ns
ip netns add app-ns

ip link add h-cl type veth peer name cl0
ip link add h-ap type veth peer name ap0
ip link set cl0 netns client-ns
ip link set ap0 netns app-ns

ip addr add 10.201.0.1/24 dev h-cl; ip link set h-cl up
ip addr add 10.200.0.1/24 dev h-ap; ip link set h-ap up

ip -n client-ns addr add 10.201.0.2/24 dev cl0
ip -n client-ns link set cl0 up
ip -n client-ns link set lo up
ip -n client-ns route add default via 10.201.0.1

ip -n app-ns addr add 10.200.0.2/24 dev ap0
ip -n app-ns link set ap0 up
ip -n app-ns link set lo up
# fault 1: app-ns has NO default route (replies to other subnets have nowhere to go)

# fault 2: the router does not forward
sysctl -qw net.ipv4.ip_forward=0

# fault 3: a security change blocked "the legacy admin port" 9000 on the router
iptables -I FORWARD -p tcp --dport 9000 -m comment --comment "SEC-204 block legacy admin port" -j DROP

# the service
mkdir -p "$S/h03-www"
echo "inventory-api OK" > "$S/h03-www/index.html"
ip netns exec app-ns setsid nohup python3 -m http.server 9000 --bind 10.200.0.2 --directory "$S/h03-www" \
    >/dev/null 2>&1 < /dev/null &
echo $! > "$S/h03-server.pid"
sleep 1
