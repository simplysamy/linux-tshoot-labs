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
