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
