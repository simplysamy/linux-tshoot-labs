# H06 - "Cannot assign requested address"

**Level:** Hard · **Time:** 45 min · **Skills:** TCP states, TIME_WAIT, ephemeral port range, `ss -s`, sysctl persistence, myths vs. facts

## Ticket

> **INC-3006 · P1**
> Since this morning `price-sync` logs thousands of failed syncs and the on-host monitoring
> check (`curl http://localhost/health`) flaps between OK and CRITICAL.
> Customers outside are fine. The app logs look normal. CPU, memory and disk are fine.
> Yesterday two changes went live:
> - **CHG-701** "network tuning from a blog post" (kernel settings)
> - `price-sync.service` was deployed - it pulls prices from the shop all the time and
>   **must keep running**.
> A colleague suggests enabling `tcp_tw_recycle`. Find the real cause and fix it properly.

## Success criteria

- 30 local requests in a row return 200; price-sync reports no errors
- The ephemeral port range is sane at runtime **and** after reboot
- `price-sync` runs and no longer burns a new connection per request
- No mass of `TIME_WAIT` sockets

Check with `sudo ./labctl.sh check h06`.

## Hints

<details><summary>Hint 1 - which error, from which component?</summary>

`curl -v localhost/` a few times. `journalctl -u price-sync -n 20`.
What does errno 99 `Cannot assign requested address` mean for an outgoing `connect()`?
Why are outside customers not affected?
</details>

<details><summary>Hint 2 - count sockets by state</summary>

`ss -s`, `ss -tan state time-wait | wc -l`, `ss -tan state time-wait | awk '{print $4}' | sort | uniq -c | sort -rn | head`.
Who opens all these connections? `sudo ss -tanp | grep -c price-sync` / `journalctl -u price-sync`.
</details>

<details><summary>Hint 3 - how many ports are there?</summary>

`sysctl net.ipv4.ip_local_port_range net.ipv4.tcp_tw_reuse net.ipv4.tcp_fin_timeout`.
`grep -r . /etc/sysctl.d/ /etc/sysctl.conf | grep -v '^.*:#'`. How long does a socket stay in TIME_WAIT?
How many new connections per second can you make with N ports?
</details>

## What you should learn

- Every outgoing TCP connection needs a free local port. The side that closes first keeps the
  4-tuple in **TIME_WAIT for 60 s** (fixed in Linux, *not* `tcp_fin_timeout`).
- Max new connections/s to one destination ≈ ports in range / 60.
- `tcp_tw_recycle` was removed from Linux 4.12 (it broke NAT clients). `tcp_tw_reuse` helps outgoing
  connections only. The real fix is connection reuse (keep-alive / pooling).
- Blog-post sysctl tuning without measuring is a classic incident cause.

Solution: [SOLUTION.md](SOLUTION.md)
