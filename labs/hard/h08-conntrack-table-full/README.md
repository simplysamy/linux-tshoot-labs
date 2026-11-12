# H08 - Random connection timeouts, nothing in the app logs

**Level:** Hard · **Time:** 60 min · **Skills:** netfilter conntrack, kernel log, `conntrack -C/-S`, sysctl persistence, finding a connection leak

## Ticket

> **INC-3008 · P1**
> Many new connections to the shop hang for 1-3 seconds or time out, at random.
> Connections that are already open work fine. New SSH logins are slow too.
> shopapp and nginx logs show nothing unusual. CPU, memory, disk are fine.
> Recent changes:
> - **CHG-830** "reduce kernel memory on small VMs"
> - `metrics-scraper.service` v2 was rolled out (it scrapes the local metrics exporter on :9100).
>   Monitoring needs it - **keep it running**.
>
> Do not remove the firewall's `SEC-099` rule.

## Success criteria

- 30 new connections in a row succeed quickly
- No `nf_conntrack: table full` messages any more
- The conntrack limit is sane at runtime and after reboot (≥ 16384)
- metrics-scraper still runs, with a sane connection pool

Check with `sudo ./labctl.sh check h08`.

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

### dmesg / journalctl -k - the kernel's messages

```bash
dmesg                           # 1. kernel ring buffer (needs sudo on some systems)
dmesg -T                        # 2. -T = readable timestamps
sudo dmesg -T | tail -5         # 3. only the newest lines
journalctl -k --since "1 hour ago"    # 4. kernel log from the journal, time window
journalctl -k | grep -iE 'oom|ext4'   # 5. filter for what you suspect
```

### conntrack - the kernel connection table

```bash
sudo conntrack -C                                # 1. how many entries now (-C = count)
sysctl net.netfilter.nf_conntrack_max            # 2. the limit
sudo conntrack -S | head -2                      # 3. statistics; 'drop' / 'early_drop' rising = table full
sudo conntrack -L -p tcp | head                  # 4. list entries (-p tcp)
sudo conntrack -L -p tcp 2>/dev/null | grep -o 'dport=[0-9]*' | sort | uniq -c | sort -rn | head -3   # 5. who fills it? count per destination port
```

### sysctl - read and change kernel settings

```bash
sysctl vm.swappiness                    # 1. read one setting
sysctl -a | grep swappiness             # 2. list all, filter (when you do not know the exact name)
sudo sysctl -w vm.swappiness=60         # 3. -w = set NOW (lost at reboot)
cat /etc/sysctl.d/*.conf                # 4. where permanent values live
sudo sysctl --system                    # 5. re-read all files; the LAST file wins on a conflict
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

## Hints

<details><summary>Hint 1 - no app log? ask the kernel</summary>

When packets vanish before they reach a process, the kernel log is the place:
`sudo dmesg -T | tail -20` or `journalctl -k -n 20`.
</details>

<details><summary>Hint 2 - the connection tracking table</summary>

`sudo conntrack -C` (count) vs `sysctl net.netfilter.nf_conntrack_max`. `sudo conntrack -S` shows
`drop`/`early_drop` per CPU. Who fills it?
`sudo conntrack -L -p tcp 2>/dev/null | grep -o 'dport=[0-9]*' | sort | uniq -c | sort -rn | head`.
</details>

<details><summary>Hint 3 - two changes, two causes</summary>

`grep -r conntrack /etc/sysctl.d/`. And: how many connections does metrics-scraper hold open?
`ss -tn state established '( dport = :9100 )' | wc -l`, `journalctl -u metrics-scraper`, its config file.
</details>

## What you should learn

- With iptables/nftables stateful rules, **every** connection uses a conntrack entry - even on loopback.
- When the table is full the kernel **drops new packets**: clients see SYN retransmits (1 s, 3 s ...).
  Established flows keep working - a typical "random" pattern.
- `dmesg` is the first stop when packets vanish below the application.
- Raising a limit is half a fix - find who fills the table (here: a connection pool of 1500).

Solution: [SOLUTION.md](SOLUTION.md)
