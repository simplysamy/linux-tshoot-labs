# E05 - Wrong page on port 80

**Level:** Easy · **Time:** 15 min · **Skills:** listening sockets, process to service mapping

## Ticket

> **INC-1005 · P1 · Customer facing**
> Customers see an old page *"Maintenance status: ALL GREEN (legacy page, 2021)"*
> instead of the shop. Someone ran `systemctl start nginx` and it failed.
> Restore the shop and make sure this does not come back after a reboot.

## Success criteria

- nginx owns port 80 and serves shopapp
- The thing that took port 80 is stopped **and** will not start at boot

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### ss - who is listening / connected?

```bash
ss                              # 1. all sockets (long)
ss -l                           # 2. -l = only listening sockets
ss -lt                          # 3. -t = TCP only
ss -ltn                         # 4. -n = numbers, no name lookup
ss -ltnp                        # 5. -p = which process owns each socket (needs sudo)
ss -ltnp 'sport = :80'          # 6. filter: only source (local) port 80
```

### ps / pgrep / pstree - look at processes

```bash
ps                                         # 1. only your shell
ps -ef                                     # 2. every process, full format (PID, PPID, command)
ps -fp 1234                                # 3. just one PID
ps -eo pid,ppid,user,%cpu,%mem,cmd         # 4. -o = choose your own columns
ps -eo pid,%cpu,cmd --sort=-%cpu | head    # 5. sort by CPU, highest first (- = descending), top 10
pgrep -af nginx                            # 6. find PIDs by name (-a = show full command, -f = match whole command line)
pstree -ps 1234                            # 7. parent chain of one PID: who started it?
```

### systemctl + journalctl - service state and logs

```bash
systemctl status nginx                          # 1. state, last exit code, last log lines
systemctl is-active nginx                       # 2. one word: active / failed / inactive
journalctl -u nginx                             # 3. the whole log of one unit (-u = unit)
journalctl -u nginx -n 20                       # 4. only the last 20 lines
journalctl -u nginx -n 20 --no-pager            # 5. print straight to the terminal (no less)
journalctl -u nginx --since "10 min ago"        # 6. time window instead of line count
```

## Hints

<details><summary>Hint 1 - why won't nginx start?</summary>

`journalctl -u nginx -n 20` - look for `bind() ... failed (98: Address already in use)`.
</details>

<details><summary>Hint 2 - who has the port?</summary>

`sudo ss -ltnp 'sport = :80'` or `sudo lsof -i :80` gives you the PID.
</details>

<details><summary>Hint 3 - PID to service</summary>

`systemctl status <PID>` tells you which systemd unit owns that process.
Killing the PID is not enough if the unit has `Restart=always`.
</details>

## What you should learn

- `Address already in use` = another socket holds the port. `ss -ltnp` finds the owner.
- `systemctl status <PID>` maps any PID to its unit (or `ps -o unit= -p <PID>`).
- `kill` treats the symptom; `systemctl disable --now` fixes the cause.

Solution: [SOLUTION.md](SOLUTION.md)
