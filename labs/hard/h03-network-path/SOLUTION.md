# H03 - Solution

Shortcuts used below:

```bash
C="sudo ip netns exec client-ns"
A="sudo ip netns exec app-ns"
```

## 1. Is the service up? (start at the destination)

```bash
$A ss -ltnp                                  # LISTEN 10.200.0.2:9000 python3 -> yes
$A curl -s 10.200.0.2:9000                   # inventory-api OK -> app is fine
```

## 2. Client side, hop by hop

```bash
$C ip addr show cl0                          # 10.201.0.2/24
$C ip route                                  # default via 10.201.0.1
$C ping -c2 10.201.0.1                       # gateway OK
$C ping -c2 -W1 10.200.0.2                   # 100% packet loss
$C curl -s --max-time 3 10.200.0.2:9000      # timeout
```

## 3. Fault 1 - the router does not forward

```bash
sudo tcpdump -ni h-cl icmp &                 # requests arrive from client...
sudo tcpdump -ni h-ap icmp                   # ...but nothing leaves to app side
sysctl net.ipv4.ip_forward                   # = 0
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward = 1' | sudo tee /etc/sysctl.d/90-router.conf
sudo sysctl --system | grep ip_forward
```

Ping again: still 100% loss. Each fix moves the failure - keep going.

## 4. Fault 2 - no return route in app-ns

```bash
sudo tcpdump -ni h-ap icmp
# 10.201.0.2 > 10.200.0.2: ICMP echo request      <-- arrives at the server side
#                                                  <-- no echo reply
$A ip route
# 10.200.0.0/24 dev ap0 proto kernel scope link src 10.200.0.2    <-- no default route!
$A ip route get 10.201.0.2
# RTNETLINK answers: Network is unreachable
$A ip route add default via 10.200.0.1
$C ping -c2 10.200.0.2                       # works now
$C curl -s --max-time 3 10.200.0.2:9000      # still timeout!
```

ICMP works but TCP 9000 does not -> something filters by port.

## 5. Fault 3 - the firewall on the router

```bash
sudo iptables -L FORWARD -nv --line-numbers
# num pkts bytes target prot ... dpt:9000 /* SEC-204 block legacy admin port */
#  1     6   360  DROP   tcp  ...
```

Counter goes up each time you curl -> this rule drops our traffic.
Port 9000 is inventory-api, not a "legacy admin port". Talk to security (change ticket), then:

```bash
sudo iptables -D FORWARD 1                   # or: -D FORWARD -p tcp --dport 9000 -m comment --comment "..." -j DROP
$C curl -s 10.200.0.2:9000                   # inventory-api OK
```

Persist firewall changes in whatever the host uses (`iptables-save > /etc/iptables/rules.v4`
with `iptables-persistent`, nftables config, ufw, or your config management) - otherwise the
old rule (or no rule) comes back after reboot.

## Root cause summary

| # | Layer | Fault | Tool that found it |
|---|-------|-------|--------------------|
| 1 | L3 router | `ip_forward=0` | tcpdump on both router legs, sysctl |
| 2 | L3 server | no default/return route in app-ns | tcpdump (request, no reply), `ip route get` |
| 3 | L4 filter | FORWARD DROP for tcp/9000 (wrong port in SEC-204) | `iptables -L -nv` counters |

**Prevent:** connectivity probes from each network (synthetic checks); peer review of firewall
changes with port ownership; manage routes/sysctl/firewall in config management.
