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
