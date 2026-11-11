# H10 - Slow app, idle host

**Level:** Hard · **Time:** 45 min · **Skills:** cgroup v2 CPU limits, CPU throttling (`cpu.stat`), systemd slices and drop-ins, `systemd-cgtop`, layered config

## Ticket

> **INC-3010 · P2**
> Shop latency went from ~5 ms to **seconds**; some requests end in `504 Gateway Timeout`.
> The host is **80-90% idle** - "it can't be CPU". No deploy happened.
> Last week FinOps ran **FINOPS-77 "right-size noisy services"** on this host.
> `traffic-replay.service` replays a share of production traffic for canary testing - it is
> expected load and **must keep running**.
> Make the shop fast again and leave the host in a clean state.

## Success criteria

- Average latency of `curl localhost/` under 200 ms, no request over 1 s, with traffic-replay running
- shopapp is not CPU-throttled any more (no limit on the service **or** on its slice below 50%)
- traffic-replay still runs

Check with `sudo ./labctl.sh check h10`.

## Hints

<details><summary>Hint 1 - host idle != process has CPU</summary>

`top` shows the host. What does the service get? `systemd-cgtop` (sort by CPU), and
`systemctl status shopapp` (look at the `CGroup:` line). Look at the cgroup's own counters:
`cat /sys/fs/cgroup/<path>/cpu.stat` - `nr_throttled`, `throttled_usec`.
</details>

<details><summary>Hint 2 - where do limits come from?</summary>

`systemctl cat shopapp` shows the unit **and all drop-ins**.
`systemctl show shopapp -p CPUQuotaPerSecUSec -p Slice`. A unit can also be limited by its **parent slice**:
`systemctl cat <slice>`, `cat /sys/fs/cgroup/<slice>/cpu.max`.
</details>

<details><summary>Hint 3 - fix it cleanly</summary>

Remove the FINOPS-77 drop-ins / slice (or raise them to something reasonable), `daemon-reload`,
restart. Check `cpu.max` again on every level of the path: `max 100000` = no limit.
</details>

## What you should learn

- Throttling is invisible in host-level `top`: the host is idle while one cgroup waits for its quota.
- `cpu.max` = `<quota> <period>`, e.g. `5000 100000` = 5% of one CPU. `nr_throttled` growing = you hit it.
- Limits stack: service, then slice, then parent slice. The tightest one wins.
- `systemctl cat` and `systemd-delta` show drop-ins that silently change units.

Solution: [SOLUTION.md](SOLUTION.md)
