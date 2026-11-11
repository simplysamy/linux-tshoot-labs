# H04 - "The server is slow" (and the obvious suspect is innocent)

**Level:** Hard · **Time:** 45 min · **Skills:** USE method, CPU vs. IO wait, per-process IO, systemd timers

## Ticket

> **INC-3004 · P2**
> Everything on the box feels slow: shell commands lag, `apt` and file writes crawl,
> shopapp latency is up. The junior on shift says: *"top shows `batch-encoder` at 100% CPU.
> I'll kill it."* - **Stop. Don't kill anything yet.**
> `batch-encoder` is an approved job that is *supposed* to use idle CPU.
> Find the real bottleneck with evidence, fix it, and keep `batch-encoder` running.

## Success criteria

- `batch-encoder` still running at nice 19
- The real cause stopped **or** limited so it cannot hurt the box, and it won't come back unconstrained
- You can explain with numbers why batch-encoder was *not* the cause

## Hints

<details><summary>Hint 1 - look at all resources, not only CPU</summary>

USE method: for each resource (CPU, memory, disk, network) check **U**tilisation,
**S**aturation, **E**rrors. Start with `vmstat 1 5` - read `r`, `b`, `us`, `sy`, `id`, `wa`.
In `top`, the header line `%Cpu(s)` has `ni` and `wa` - what do they mean?
</details>

<details><summary>Hint 2 - which disk, which process?</summary>

`iostat -xz 1 3` - look at `w/s`, `w_await`, `%util`.
`sudo pidstat -d 1 5` or `sudo iotop -o` shows IO per process.
`ps -eo pid,stat,wchan:20,cmd | awk '$2 ~ /D/'` shows tasks blocked on IO.
</details>

<details><summary>Hint 3 - it comes back</summary>

`systemctl status <PID>` shows the unit. Look for a `TriggeredBy:` line.
`systemctl list-timers --all`. Stopping the service is not enough if a timer restarts it.
Options: stop + disable the timer, or keep it but give it a low IO priority
(`sudo systemctl edit audit-sync.service` -> `IOSchedulingClass=idle` / `IOWeight=` / `IOWriteBandwidthMax=`).
</details>

## What you should learn

- High CPU from a **niced** process is mostly harmless: the scheduler gives CPU to normal tasks first. `ni` in top.
- `wa` (iowait) high + processes in `D` state + disk `%util` high = **IO bottleneck**.
- Small synchronous writes (`O_DSYNC`, `fsync`) can saturate a disk at low MB/s.
- Evidence before action. Killing the obvious suspect would have hurt the business and fixed nothing.
- systemd timers restart work just like cron. `TriggeredBy:` tells you.

Solution: [SOLUTION.md](SOLUTION.md)
