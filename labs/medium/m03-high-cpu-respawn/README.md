# M03 - High CPU that keeps coming back

**Level:** Medium · **Time:** 25 min · **Skills:** load average, top/ps, process trees, cron

## Ticket

> **INC-2003 · P2**
> Server is slow, load average is high, CPU is pinned at 100%.
> The night shift "killed the process" twice. Each time the CPU went back to
> 100% about a minute later. Find what it is, why it comes back, and stop it for good.
> The search team owns the job - leave a note for them, do not delete their script.

## Success criteria

- The CPU hog is not running
- Nothing will start it again
- shopapp still healthy

## Hints

<details><summary>Hint 1 - who is using CPU?</summary>

`uptime` (load vs. CPU count from `nproc`), then `top` (press `P` to sort by CPU, `1` for per-CPU),
or `ps -eo pid,ppid,user,ni,%cpu,etime,cmd --sort=-%cpu | head`.
</details>

<details><summary>Hint 2 - who started it?</summary>

Look at the parent PID chain: `pstree -ps <PID>`. What is at the top?
`systemctl status <PID>` also shows the unit (cgroup) it belongs to.
</details>

<details><summary>Hint 3 - where is it scheduled?</summary>

`grep -r reindex /etc/cron* /var/spool/cron 2>/dev/null` and `systemctl list-timers`.
`journalctl -u cron --since "10 min ago"` shows every cron run.
</details>

## What you should learn

- Load average = runnable (+ uninterruptible) tasks. Compare it to `nproc`.
- Killing a PID is not a fix if a scheduler (cron, systemd timer, supervisor, k8s) restarts it.
- `pstree -ps` and `systemctl status <PID>` answer "who started this?".
- Disable (comment out) and leave a note instead of deleting other teams' work.

Solution: [SOLUTION.md](SOLUTION.md)
