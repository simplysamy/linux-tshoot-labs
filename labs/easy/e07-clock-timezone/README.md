# E07 - Wrong time on the server

**Level:** Easy · **Time:** 15 min · **Skills:** timedatectl, NTP sync, timezones, restarting services after a change

## Ticket

> **INC-1007 · P3**
> The log team cannot correlate incidents: timestamps in `/var/log/shopapp/app.log` on
> tshoot-lab are hours away from every other server. All our servers run in **UTC**.
> Monitoring also fires `ClockNotSynchronised` for this host.
> The host was built from a "customised" image last week.
> Fix the clock and make sure the app logs correct UTC times.

## Success criteria

- System timezone is UTC
- NTP synchronisation is enabled and a time sync service is running
- New lines in `app.log` carry the current UTC time

Check with `sudo ./labctl.sh check e07`.

## Hints

<details><summary>Hint 1 - one command shows it all</summary>

`timedatectl` shows local time, UTC time, timezone, "System clock synchronized"
and "NTP service". Compare `date` and `date -u`.
</details>

<details><summary>Hint 2 - two separate problems</summary>

A wrong *timezone* only changes how time is displayed. A wrong *clock* is really wrong.
Here you have both. `timedatectl set-timezone`, `timedatectl set-ntp`.
Is the sync service running? `systemctl status systemd-timesyncd` (or `chrony`).
</details>

<details><summary>Hint 3 - the app still logs the old zone</summary>

A running process read the timezone when it started. What do you need to do
so shopapp picks up the new one?
</details>

## What you should learn

- `timedatectl` is the one place to check time, zone and sync.
- Servers should run in UTC; convert to local time only when you display.
- NTP off = the clock drifts; drift breaks TLS, Kerberos, cron, log correlation.
- Many settings (timezone, env vars, limits) are read at process start - restart to apply.

Solution: [SOLUTION.md](SOLUTION.md)
