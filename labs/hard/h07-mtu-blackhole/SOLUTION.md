# H07 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

Shortcut used below: `C="sudo ip netns exec cust-ns"`, `V="sudo ip netns exec vpn-ns"`, `D="sudo ip netns exec dc-ns"`.

## 1. Reproduce

```bash
$C curl -s http://10.230.2.2:8000/small.txt                 # OK
$C curl -o /dev/null -m 20 -w '%{size_download}\n' http://10.230.2.2:8000/catalog.bin
# curl: (28) Operation timed out ... 0 bytes received
```

The TCP handshake and the HTTP request work (small packets). The response (big packets) never arrives.

## 2. Packet size test

Test in the direction the big data flows - from the server to the partner:

```bash
$D ping -c2 -M do -s 1372 10.230.1.2      # 1372+28 = 1400 bytes -> replies
$D ping -c2 -M do -s 1472 10.230.1.2      # 1500 bytes -> no reply, and no error either
```

Anything bigger than 1400 bytes disappears **silently**. Normally the sender would get
`Frag needed and DF set (mtu = 1400)` back. It gets nothing.

## 3. Find the small link

```bash
for ns in cust-ns vpn-ns dc-ns; do echo "== $ns"; sudo ip -n $ns link | grep -v 'lo:' | grep mtu; done
# cust-ns: cl0 ... mtu 1500
# vpn-ns:  r0  ... mtu 1400   <- tunnel
#          r1  ... mtu 1500
# dc-ns:   ap0 ... mtu 1500
```

The server and the partner both have MTU 1500, so TCP agrees on MSS 1460 (1500-byte
packets). The gateway cannot forward those into the 1400-byte tunnel.

## 4. Why PMTUD doesn't save us

```bash
$D tcpdump -ni ap0 'tcp or icmp' &
$C curl -o /dev/null -m 10 http://10.230.2.2:8000/catalog.bin
# 10.230.2.2.8000 > 10.230.1.2.xxx: Flags [.], seq 1:1449, length 1448    <- retransmitted again and again
# (no ICMP "need to frag" ever arrives)
$V iptables -L OUTPUT -n -v
# DROP icmp -- 0.0.0.0/0 0.0.0.0/0  /* SEC-311 no ICMP from VPN gateway */   pkts 37
```

The gateway does create ICMP "fragmentation needed, MTU 1400" - and SEC-311 drops it on
the way out. The server never learns the smaller MTU and retransmits 1500-byte packets forever.

## 5. Fix (either - both is best)

**a) Let PMTUD work** - allow ICMP frag-needed before the drop (keep the rest of SEC-311):

```bash
$V iptables -I OUTPUT 1 -p icmp --icmp-type fragmentation-needed -j ACCEPT
```

**b) MSS clamping on the gateway** - rewrite the MSS in SYNs so neither side sends packets
bigger than the tunnel: 1400 - 20 (IP) - 20 (TCP) = 1360.

```bash
$V iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360
```

(`--clamp-mss-to-pmtu` uses the MTU of the *outgoing* interface of each SYN; the client's SYN
leaves via `r1` (1500), so here it would not help for the server's data. `--set-mss` is explicit.)

Wrong fixes: raising `r0` to 1500 (the provider's tunnel cannot carry it), lowering `cl0`
(not our machine), disabling DF on the server.

## 6. Verify

```bash
$C curl -o /dev/null -w '%{size_download} bytes in %{time_total}s\n' http://10.230.2.2:8000/catalog.bin
$D tracepath -n 10.230.1.2        # shows pmtu 1400 once ICMP is allowed
sudo ./labctl.sh check h07
```

## Root cause and prevention

| | |
|---|---|
| Root cause | New tunnel MTU 1400 + SEC-311 dropping all ICMP from the gateway = PMTUD black hole |
| Fix | Allow ICMP type 3 code 4 and/or clamp MSS to 1360 on the gateway |
| Prevent | ICMP policy that keeps dest-unreachable; MSS clamping as standard on every tunnel; synthetic check that downloads a big file, not only a tiny health URL |
