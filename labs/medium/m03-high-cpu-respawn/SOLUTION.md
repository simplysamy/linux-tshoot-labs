# M03 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. Size the problem

```bash
uptime            # load average: 2.10, 1.80, 1.05   (with nproc = 2 -> fully busy)
nproc
top -o %CPU       # python3 processes at ~100% each
ps -ef                                                    # 1. all processes
ps -eo pid,ppid,user,%cpu,cmd                             # 2. choose columns
ps -eo pid,ppid,user,%cpu,cmd --sort=-%cpu                # 3. + highest CPU first
ps -eo pid,ppid,user,ni,%cpu,etime,cmd --sort=-%cpu | head -5   # 4. + nice value, run time, only top 5
#  PID  PPID USER NI %CPU ELAPSED CMD
# 4102  4100 root  0 99.5   01:12 /usr/bin/python3 /usr/local/bin/shopapp-reindex
# 4103  4100 root  0 99.1   01:12 /usr/bin/python3 /usr/local/bin/shopapp-reindex
```

## 2. Who started it?

```bash
pstree -ps 4102
# systemd(1)---cron(650)---cron(4098)---sh(4099)---flock(4100)---python3(4101)---python3(4102)
```

(The very first copy was started by hand by the lab, so it may show `systemd(1)---flock`.
After you kill it, the next copy clearly comes from cron.)

```bash
grep -r reindex /etc/cron* /var/spool/cron 2>/dev/null
# /etc/cron.d/shopapp-reindex:* * * * * root /usr/bin/flock -n ... /usr/local/bin/shopapp-reindex
journalctl -u cron --since "5 min ago" | grep reindex
```

Every minute cron tries to start it; `flock -n` only blocks duplicates. Kill it -> lock free -> cron starts it again.

## 3. Fix - in the right order

Disable the scheduler **first**, then kill:

```bash
sudo sed -i 's/^\* \* \* \* \* root/# DISABLED INC-2003 runaway CPU, see ticket\n#* * * * * root/' /etc/cron.d/shopapp-reindex
cat /etc/cron.d/shopapp-reindex
pgrep -af shopapp-reindex                       # ALWAYS look before pkill -f
pgrep -af shopapp-reindex                                      # 1. LOOK first: which processes match?
sudo pkill -f '^/usr/bin/python3 /usr/local/bin/shopapp-reindex'   # 2. kill exactly those (^ = match from the start of the command line)
sleep 2; pgrep -af shopapp-reindex || echo "gone"
```

Why the `^` anchor? `pkill -f` matches the whole command line of **every** process.
Without the anchor, the pattern also matches `sudo pkill -f /usr/local/bin/...` itself
(its parent `sudo` has the same text in its command line) and can kill your own command,
or other things such as an editor that has the script open.

Wait 2 minutes and check again: it must not come back. Watch load drop with `uptime`.

## 4. Hand off

Tell the search team: retry loop with no sleep/backoff and no max attempts burns all CPUs.
They should add backoff, run it with `nice -n 10`, or as a systemd timer with `CPUQuota=`.

## Root cause and prevention

| | |
|---|---|
| Root cause | Reindex job busy-loops on retry; cron restarts it every minute |
| Prevent | Backoff + max retries; limit batch jobs with `nice`/`CPUQuota`; alert on load > nproc for 10 min |
