# H07 - Small requests work, big downloads hang

**Level:** Hard · **Time:** 60 min · **Skills:** MTU, Path MTU Discovery, ICMP "fragmentation needed", `ping -M do`, `tracepath`, `tcpdump`, MSS clamping

## Ticket

> **INC-3007 · P2**
> A partner reaches our catalogue service over a site-to-site VPN. Since last week:
> health checks are green, small API calls work, but downloading the catalogue export
> **hangs forever** at 0 bytes or a few KB.
> Last week two changes happened:
> - the VPN provider migrated the tunnel (new tunnel interface MTU **1400**)
> - **SEC-311** "harden VPN gateway: no ICMP"
>
> Lab topology (namespaces act as machines):
> ```
> [cust-ns] cl0 10.230.1.2 --- r0 10.230.1.1 [vpn-ns gateway] r1 10.230.2.1 --- ap0 10.230.2.2 [dc-ns] :8000
> ```
> Customer tests:
> `sudo ip netns exec cust-ns curl -s http://10.230.2.2:8000/small.txt` (works)
> `sudo ip netns exec cust-ns curl -o /dev/null -m 20 http://10.230.2.2:8000/catalog.bin` (hangs)
>
> Constraints: the tunnel MTU is fixed by the provider, and we cannot change the partner's machines.

## Success criteria

- The partner can download `catalog.bin` (500 KB) in under 20 s
- Tunnel interface `r0` still has MTU 1400; the partner's `cl0` still has MTU 1500

Check with `sudo ./labctl.sh check h07`.

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### ip / ip netns - addresses, routes, namespaces

```bash
ip addr                                  # 1. interfaces and their IPs (short: ip a)
ip -br addr                              # 2. -br = brief, one line per interface
ip route                                 # 3. routing table: 'default via X' = where unknown traffic goes
ip route get 10.0.0.5                    # 4. which route/interface would the kernel use for THIS destination?
ip netns list                            # 5. namespaces = separate mini network stacks (lab hosts)
sudo ip netns exec NAME ip route         # 6. run any command INSIDE a namespace
C="sudo ip netns exec NAME"; $C ip route # 7. shortcut variable so you type less
```

### ping -M do / tracepath - find the path MTU

```bash
ping -c2 10.0.0.2                         # 1. small packets work
ping -c2 -s 1472 10.0.0.2                 # 2. -s = payload size (+28 bytes headers = 1500 on the wire)
ping -c2 -M do -s 1472 10.0.0.2           # 3. -M do = 'Do not fragment' - too big -> error or silence
tracepath -n 10.0.0.2                     # 4. finds the smallest MTU on the path (-n = no names)
ip link | grep mtu                        # 5. MTU of each local interface
```

### tcpdump - watch packets

```bash
sudo tcpdump -i eth0                      # 1. every packet on an interface (very noisy)
sudo tcpdump -ni eth0                     # 2. -n = no name lookups
sudo tcpdump -ni eth0 icmp                # 3. filter: only ping
sudo tcpdump -ni eth0 port 80             # 4. filter: only port 80
sudo tcpdump -ni eth0 'tcp port 80 and host 10.0.0.5'   # 5. combine with and/or
sudo tcpdump -ni eth0 -c 5 icmp           # 6. -c 5 = stop after 5 packets
# Reading it: packets arrive on one side but nothing leaves the other side -> something in between drops/does not forward.
```

### iptables - read the firewall

```bash
sudo iptables -L                              # 1. list rules (all chains)
sudo iptables -L INPUT                        # 2. one chain: INPUT = traffic TO this host; FORWARD = through; OUTPUT = from
sudo iptables -L INPUT -n                     # 3. -n = numbers, no DNS (much faster)
sudo iptables -L INPUT -n -v                  # 4. -v = packet/byte counters: does the number rise when you test? -> that rule hits
sudo iptables -L INPUT -n -v --line-numbers   # 5. rule numbers, so you can delete/insert by number
sudo iptables -S                              # 6. the same rules as commands (easy to copy, grep)
# change:  -D INPUT 1  (delete rule 1)   -I INPUT 1 <rule>  (insert at top)   -A  (append at end)
```

## Hints

<details><summary>Hint 1 - size matters</summary>

Small works, big hangs: suspect packet size. `ip -n <ns> link` shows MTUs on every hop.
Test in the direction the big data flows (server -> partner):
`sudo ip netns exec dc-ns ping -M do -s 1372 10.230.1.2` vs `... -s 1472 ...`
(`-M do` = don't fragment, 28 bytes of IP+ICMP headers).
</details>

<details><summary>Hint 2 - how is TCP supposed to learn the path MTU?</summary>

Linux sets DF on TCP packets. A router that cannot forward a too-big DF packet drops it and
sends back ICMP type 3 code 4 "fragmentation needed". The sender then uses smaller packets.
What happens if that ICMP never arrives? `sudo ip netns exec vpn-ns iptables -L -n -v`.
</details>

<details><summary>Hint 3 - see it</summary>

`sudo ip netns exec dc-ns tcpdump -ni ap0 'tcp or icmp'` while the download hangs: the server
retransmits the same big segment again and again. Two fixes: let ICMP frag-needed through,
or clamp the TCP MSS on the gateway.
</details>

## What you should learn

- The classic MTU black hole: handshake and small packets work, bulk data hangs.
- "Block all ICMP" breaks Path MTU Discovery. Allow at least type 3 (dest-unreachable), code 4.
- MSS clamping on tunnel gateways (`TCPMSS`) is the standard belt-and-braces fix.
- `ping -M do -s <size>` and `tracepath` find the real path MTU.

Solution: [SOLUTION.md](SOLUTION.md)
