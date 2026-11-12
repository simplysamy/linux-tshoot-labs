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

### uptime / top - CPU

```bash
uptime                  # 1. load average: 1, 5, 15 min. Compare to the CPU count:
nproc                   # 2. number of CPUs. load 2.0 on 2 CPUs = fully busy
top                     # 3. live view. P = sort by CPU, M = by memory, 1 = per-CPU, q = quit
top -bn1 | head -5      # 4. -b = batch (plain text), -n1 = one snapshot -> good for logs and pipes
# CPU line: us=user sy=kernel ni=niced id=idle wa=waiting for disk
```

### cgroups - limits systemd puts on a service

```bash
systemctl show -p MemoryMax -p TasksMax -p CPUQuotaPerSecUSec nginx   # 1. limits systemd configured
systemd-cgtop -n 1                              # 2. top, but per cgroup/service
cat /sys/fs/cgroup/system.slice/nginx.service/cpu.max   # 3. the kernel's number: 'max 100000' = no cap, '5000 100000' = 5% of one CPU
cat /sys/fs/cgroup/system.slice/nginx.service/cpu.stat  # 4. nr_throttled rising = the cap is biting
systemd-delta --type=extended                   # 5. every drop-in override on the host
```

### systemctl show / cat - ask systemd for facts

```bash
systemctl cat nginx                              # 1. the unit file(s) systemd really uses, incl. drop-ins
systemctl show nginx                             # 2. every property (long)
systemctl show -p User nginx                     # 3. -p = just one property
systemctl show -p User -p MainPID nginx          # 4. several
systemctl show -p MainPID --value nginx          # 5. --value = print only the value (for scripts)
```

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
