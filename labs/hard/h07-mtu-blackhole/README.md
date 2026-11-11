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
