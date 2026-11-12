# E08 - "Works when I run it"

**Level:** Easy · **Time:** 15 min · **Skills:** systemd job failures, exit code 127, PATH, login vs non-login environments

## Ticket

> **INC-1008 · P4**
> The stock report `/srv/backups/shop-report.txt` has not been updated since the
> **shoptools** package was upgraded. It is produced by `shopapp-report.service`
> (started by a timer every 5 minutes).
> The developer says: *"The script works fine, I just ran it in my shell."*
> Make the scheduled job work again.

## Success criteria

- `systemctl start shopapp-report` succeeds
- `/srv/backups/shop-report.txt` is fresh and contains the stats
- The timer is still enabled

Check with `sudo ./labctl.sh check e08`.

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### PATH - where commands are found

```bash
echo $PATH                         # 1. directories searched, in order, separated by :
type shopctl                       # 2. where would the shell run it from? (or 'not found')
command -v shopctl                 # 3. same, script-friendly
systemctl show-environment | grep ^PATH   # 4. the PATH systemd (and so services) use - not your shell's
```

### sed - edit text from the command line

```bash
sed 's/old/new/' file           # 1. print file with the first 'old' on each line replaced (file unchanged)
sed 's/old/new/g' file          # 2. g = every match on the line
sed -n '3p' file                # 3. -n + p = print only line 3
sed '/old/d' file               # 4. d = delete lines that match (still only printed)
sed -i 's/old/new/' file        # 5. -i = edit the file IN PLACE (make a copy first: cp file file.bak)
sed -i 's#/a/b#/c/d#' file      # 6. any delimiter works: # avoids escaping / in paths
```

### systemctl show / cat - ask systemd for facts

```bash
systemctl cat nginx                              # 1. the unit file(s) systemd really uses, incl. drop-ins
systemctl show nginx                             # 2. every property (long)
systemctl show -p User nginx                     # 3. -p = just one property
systemctl show -p User -p MainPID nginx          # 4. several
systemctl show -p MainPID --value nginx          # 5. --value = print only the value (for scripts)
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

<details><summary>Hint 1 - what did systemd see?</summary>

`systemctl status shopapp-report` - look at `status=` in the `Main PID` / `Process` line.
`journalctl -u shopapp-report -n 20`. Which exit code is it and what does it mean?
</details>

<details><summary>Hint 2 - compare environments</summary>

`type shopctl` in your login shell. Where does it live? Who adds that directory to your PATH?
(`grep -r shoptools /etc/profile /etc/profile.d/ ~/.bashrc`).
What is PATH for a systemd service? `systemctl show-environment`.
</details>

<details><summary>Hint 3 - fix options</summary>

Use the full path in the script, or set `Environment=PATH=...` in the unit (drop-in),
or link the tool into a standard directory. Pick one and know why.
</details>

## What you should learn

- Exit code **127** = command not found. **126** = found but not executable.
- systemd services and cron do **not** read `/etc/profile`, `~/.bashrc` or `/etc/profile.d`.
  Their PATH is short and fixed.
- "Works in my shell" means "my shell's environment is different" - compare env, user, cwd.
- Scripts run by machines should use full paths or set PATH themselves.

Solution: [SOLUTION.md](SOLUTION.md)
