# M05 - Backups silently stopped

**Level:** Medium · **Time:** 30 min · **Skills:** cron rules, syslog/journal, file modes, testing jobs by hand

## Ticket

> **INC-2005 · P2 · Audit finding**
> Audit found `/srv/backups` is **empty**. A new backup job was "deployed" last week by copying
> two files to the server: `/etc/cron.d/shopapp-backup.cron` and `/usr/local/bin/shopapp-backup`.
> No errors were ever reported. Make the backups run.
> (In the lab the job runs every minute so you can test quickly.)

## Success criteria

- cron runs the job and a fresh `.tar.gz` appears in `/srv/backups`
- The archive is valid

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### cron - is my job running?

```bash
ls -l /etc/cron.d/                              # 1. system cron files: names, owner, mode
cat /etc/cron.d/NAME                            # 2. format: min hour day month weekday USER command
journalctl -u cron --since "10 min ago"         # 3. every run, and every complaint
systemctl list-timers                           # 4. the systemd equivalent
sudo /path/to/script                            # 5. run the job by hand to see its real error
```

### mv / chmod / tar - the small fixes

```bash
mv old.name new.name                  # 1. rename
chmod 0644 file                       # 2. rw-r--r--
chmod 0755 script                     # 3. rwxr-xr-x  (a script needs x to run)
tar -tzf backup.tar.gz | head         # 4. -t = list (not extract), -z = gzip, -f = this file
tar -tzvf backup.tar.gz | head        # 5. -v = with sizes/dates: look inside a backup before you trust it
```

## Hints

<details><summary>Hint 1 - does cron even see it?</summary>

`journalctl -u cron --since "10 min ago"` - do you see the job running each minute?
Read `man cron` about `/etc/cron.d` - there are rules about file **names**.
</details>

<details><summary>Hint 2 - cron is picky</summary>

After fixing the name, read the cron log again. cron also refuses files that are
writable by group/other or not owned by root (security reasons).
</details>

<details><summary>Hint 3 - run it like cron does</summary>

Run the exact command from the cron line by hand: `sudo /usr/local/bin/shopapp-backup`.
Cron does not run `bash script`, it executes the path directly.
</details>

## What you should learn

- "No errors" from cron often means "never ran". Check the cron log first.
- `/etc/cron.d` file rules: name only `[A-Za-z0-9_-]` (no `.`), owned by root, not group/world writable, has a **user** column.
- Run the exact command as the exact user cron uses before you trust a job.
- A job that fails silently needs monitoring: alert when the newest backup is older than X.

Solution: [SOLUTION.md](SOLUTION.md)
