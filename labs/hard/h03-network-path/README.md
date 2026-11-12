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

### ping / curl - test hop by hop

```bash
ping -c2 10.201.0.1                        # 1. the first hop (your gateway)
ping -c2 -W1 10.200.0.2                    # 2. the far side; -W1 = wait only 1 s per reply
curl -s --max-time 3 10.200.0.2:9000       # 3. the actual service (TCP port!) - ping working does not prove this
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

### sysctl - read and change kernel settings

```bash
sysctl vm.swappiness                    # 1. read one setting
sysctl -a | grep swappiness             # 2. list all, filter (when you do not know the exact name)
sudo sysctl -w vm.swappiness=60         # 3. -w = set NOW (lost at reboot)
cat /etc/sysctl.d/*.conf                # 4. where permanent values live
sudo sysctl --system                    # 5. re-read all files; the LAST file wins on a conflict
```

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
