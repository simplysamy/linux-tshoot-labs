# M10 - Works on the box, down for everyone else

**Level:** Medium · **Time:** 30 min · **Skills:** listen addresses, `ss -ltn`, refused vs. timed out, INPUT firewall rules, testing from another host

## Ticket

> **INC-2010 · P1**
> External monitoring says the shop is **DOWN**. On the server itself `curl localhost/` works fine,
> so on-call closed the first alert as "false positive" - and it fired again.
> Recent changes: **CHG-610** "web tier hardening" and **SEC-118** "block scanner subnet".
> The monitoring probe lives at `10.210.0.2` (namespace `mon-ns` in the lab). Test as the probe:
> `sudo ip netns exec mon-ns curl -sv --max-time 5 http://10.210.0.1/health`
> Make the shop reachable for the probe again.

## Success criteria

- The probe gets `200` from `http://10.210.0.1/health`
- `curl localhost/` on the server still works
- `nginx -t` passes

Check with `sudo ./labctl.sh check m10`.

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### curl - talk to a web service

```bash
curl http://localhost/                                   # 1. fetch a page, print the body
curl -s http://localhost/                                # 2. -s = silent (no progress bar)
curl -s -o /dev/null http://localhost/                   # 3. -o /dev/null = throw the body away
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/   # 4. -w = print only the HTTP status code
curl -v http://localhost/                                # 5. -v = verbose: shows connect, headers (debug)
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 5 http://localhost/   # 6. + timing, + give up after 5 s
```

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

### ss - who is listening / connected?

```bash
ss                              # 1. all sockets (long)
ss -l                           # 2. -l = only listening sockets
ss -lt                          # 3. -t = TCP only
ss -ltn                         # 4. -n = numbers, no name lookup
ss -ltnp                        # 5. -p = which process owns each socket (needs sudo)
ss -ltnp 'sport = :80'          # 6. filter: only source (local) port 80
```

### nginx - test before you restart

```bash
nginx -t                                  # 1. check the config syntax, change nothing
sudo nginx -t                             # 2. needs root to read all files
sudo nginx -T                             # 3. -T = test AND print the full effective config
sudo nginx -T | grep -n listen            # 4. find one directive in it
sudo nginx -t && sudo systemctl reload nginx   # 5. && = reload only if the test passed
```

## Hints

<details><summary>Hint 1 - read the client error exactly</summary>

`Connection refused` and `Connection timed out` mean different things. Which one do you get?
Which layer does each point to? (README "How a senior SRE troubleshoots" table.)
</details>

<details><summary>Hint 2 - do the packets arrive? who drops them?</summary>

`sudo tcpdump -ni h-mon port 80` shows if SYNs arrive and if anything answers.
`sudo iptables -L INPUT -n -v --line-numbers` - watch the packet counters while the probe tries.
</details>

<details><summary>Hint 3 - after the firewall, the error changes</summary>

On which address does nginx listen? `sudo ss -ltnp | grep ':80 '`.
`0.0.0.0:80` / `*:80` = all addresses; `127.0.0.1:80` = only local. `sudo nginx -T | grep listen`.
</details>

## What you should learn

- Always test from where the user is. `localhost` skips the network, the firewall and the listen address.
- **Refused** = packet arrived, nothing listens on that address/port (or REJECT with RST).
  **Timed out** = packet dropped on the way (firewall DROP, routing).
- Fixing one layer can reveal the next one. Re-test after each change - a *changed* error is progress.
- Firewall rules: read them with counters (`-v`) and in order; narrow a rule instead of deleting it blindly.

Solution: [SOLUTION.md](SOLUTION.md)
