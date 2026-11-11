# H03 - Service unreachable across networks (layered faults)

**Level:** Hard · **Time:** 60 min · **Skills:** routing, IP forwarding, firewall, tcpdump, network namespaces

## Ticket

> **INC-3003 · P1**
> Clients on the **client network** cannot reach **inventory-api** at `http://10.200.0.2:9000`.
> The app team swears the service is up. The network team swears the network is fine.
> Find every problem along the path and fix it. The fix must survive a reboot of the router.

Setup: this VM is the **router** between two "machines". Each machine is a
Linux *network namespace* (like a container):

```
 [client-ns]                         [ this VM = router ]                         [app-ns]
 cl0 10.201.0.2/24  <----veth---->  h-cl 10.201.0.1/24                      inventory-api :9000
                                    h-ap 10.200.0.1/24  <----veth---->  ap0 10.200.0.2/24
```

Run a command "on" a machine with `sudo ip netns exec client-ns <cmd>` or `sudo ip netns exec app-ns <cmd>`.

## Success criteria

- `sudo ip netns exec client-ns curl http://10.200.0.2:9000/` returns `inventory-api OK`
- The router config is persistent

## Hints

<details><summary>Hint 1 - work layer by layer, from both ends</summary>

Is the service listening? (`ip netns exec app-ns ss -ltn`). Does it answer locally?
(`ip netns exec app-ns curl 10.200.0.2:9000`). Can the client reach its gateway?
Can the client ping the server? Go hop by hop. There is **more than one** fault.
</details>

<details><summary>Hint 2 - where do packets die?</summary>

Run `sudo tcpdump -ni h-ap` in one terminal and ping/curl from the client in another.
Do you see requests arriving at h-ap? Do you see replies? Then look at h-cl.
`ip route` in **each** namespace. A packet needs a route there **and** back.
</details>

<details><summary>Hint 3 - the router</summary>

A Linux box only routes between interfaces if `net.ipv4.ip_forward = 1`.
Routed traffic goes through the iptables **FORWARD** chain, not INPUT:
`sudo iptables -L FORWARD -nv --line-numbers`. Watch the packet counters.
</details>

## What you should learn

- Two-way thinking: a reply needs a route back. "Ping works one way" = check the return path.
- Bisect with `tcpdump` on each hop: see where the packet is last seen.
- Routers need `ip_forward=1`; routed packets hit the FORWARD chain.
- iptables counters (`-v`) show which rule is matching your traffic.
- Runtime changes (`sysctl -w`, `iptables -I`) are lost on reboot - persist them.
- When several faults stack, each fix only moves the failure. Keep testing after each change.

Solution: [SOLUTION.md](SOLUTION.md)
