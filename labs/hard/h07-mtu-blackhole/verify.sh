#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

mtu() { ip -n "$1" -o link show "$2" 2>/dev/null | grep -o 'mtu [0-9]*' | cut -d' ' -f2; }

[[ $(mtu vpn-ns r0) == 1400 ]] && pass "tunnel r0 MTU is 1400" || fail "tunnel r0 MTU is $(mtu vpn-ns r0) - the provider fixes it at 1400"
[[ $(mtu cust-ns cl0) == 1500 ]] && pass "partner cl0 MTU is 1500" || fail "partner cl0 MTU is $(mtu cust-ns cl0) - we can't change partner machines"
[[ $(mtu dc-ns ap0) == 1500 ]] || warn "server ap0 MTU changed to $(mtu dc-ns ap0) - works, but shrinks packets for every client"

small=$(ip netns exec cust-ns curl -s --max-time 5 http://10.230.2.2:8000/small.txt 2>/dev/null)
[[ $small == "catalog-api OK" ]] && pass "small request works" || fail "small request fails"

# use a fresh connection each time; flush learned PMTU so the test is honest
ip netns exec dc-ns ip route flush cache 2>/dev/null || true
size=$(ip netns exec cust-ns curl -s -o /dev/null -w '%{size_download}' --max-time 20 http://10.230.2.2:8000/catalog.bin 2>/dev/null)
[[ $size == 500000 ]] && pass "catalog.bin downloaded completely (500000 bytes)" || fail "catalog.bin download got ${size:-0} of 500000 bytes"
finish_verify
