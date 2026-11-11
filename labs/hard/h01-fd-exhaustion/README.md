# H01 - App hangs after some traffic, restart "fixes" it

**Level:** Hard · **Time:** 40 min · **Skills:** file descriptors, ulimits, /proc, systemd drop-ins, strace

## Ticket

> **INC-3001 · P1 · Customer facing · recurring**
> Since yesterday shopapp stops answering after a few minutes of traffic.
> nginx returns **504 Gateway Timeout**. CPU of the app goes high while it hangs.
> Restarting shopapp fixes it for a few minutes, then it happens again.
> The team already did 4 restarts today. We need the root cause, not another restart.

## Success criteria

- shopapp survives 300+ requests and stays healthy
- No fd leak (fd count stays low)
- Limits are sane (soft NOFILE >= 1024)

## Hints

<details><summary>Hint 1 - what does the process see?</summary>

Find the PID: `systemctl show -p MainPID shopapp`. Then count open fds:
`sudo ls /proc/<PID>/fd | wc -l`. Compare to `grep 'open files' /proc/<PID>/limits`.
`journalctl -u shopapp` - search for `Errno`.
</details>

<details><summary>Hint 2 - what are those fds?</summary>

`sudo ls -l /proc/<PID>/fd` or `sudo lsof -p <PID>`. Many fds to the same file = leak.
`sudo strace -f -p <PID> -e trace=openat,accept4` while you send one request.
</details>

<details><summary>Hint 3 - where does the limit come from?</summary>

`systemctl cat shopapp` prints the unit **and every drop-in** with file paths.
`systemctl show -p LimitNOFILE shopapp`. Two changes combined into one outage.
</details>

## What you should learn

- `EMFILE (Errno 24) Too many open files` = per-process fd limit reached.
- `/proc/<PID>/fd` and `/proc/<PID>/limits` show the real state of a running process.
  Your shell's `ulimit -n` does **not** apply to systemd services.
- `systemctl cat` reveals drop-ins in `/etc/systemd/system/<unit>.d/` that override the main unit.
- Two changes can be safe alone and break together. Raising the limit alone only delays a leak.

Solution: [SOLUTION.md](SOLUTION.md)
