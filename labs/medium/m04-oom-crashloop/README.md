# M04 - Service keeps restarting (OOM killer)

**Level:** Medium · **Time:** 25 min · **Skills:** memory, cgroups, OOM killer, kernel log, systemd

## Ticket

> **INC-2004 · P3**
> `cache-warmer.service` restarts every few seconds. Product pages are slow because the cache
> is always cold. Nobody changed the code. There was a load test (LT-88) last week.
> Find why it dies and stabilise it. Do **not** remove the memory limit - it protects the host.

## Success criteria

- cache-warmer stays up (no restarts for 20s)
- The memory limit on the unit is still in place
- The real cause is fixed

## Hints

<details><summary>Hint 1 - how does it die?</summary>

`systemctl status cache-warmer` - look at `Main PID`, the restart counter and
`Result:`. `journalctl -u cache-warmer -n 30`.
</details>

<details><summary>Hint 2 - who killed it?</summary>

The kernel logs every OOM kill: `journalctl -k | grep -i -E 'oom|killed process'`
(or `sudo dmesg -T | grep -i oom`). Is it a *global* OOM or a *cgroup* (memcg) OOM?
</details>

<details><summary>Hint 3 - why does it grow?</summary>

Watch it grow: `watch -n1 'systemctl show -p MemoryCurrent cache-warmer'` or
`ps -o pid,rss,cmd -C python3`. The program prints its config at start - read the log and `/etc/cache-warmer.conf`.
</details>

## What you should learn

- `Result: oom-kill` and `Killed process ... (oom-kill / memcg)` in the kernel log.
- cgroup limits (`MemoryMax=`) produce OOM kills even when `free -m` shows plenty of RAM.
- RSS growing in a straight line = leak or unbounded cache. Find the bound, don't raise the limit blindly.
- "Nobody changed the code" - but config changes are changes too.

Solution: [SOLUTION.md](SOLUTION.md)
