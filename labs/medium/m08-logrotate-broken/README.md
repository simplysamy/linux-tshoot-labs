# M08 - logrotate "is configured" but logs keep growing

**Level:** Medium · **Time:** 30 min · **Skills:** logrotate debugging, directory permissions, `create` vs `copytruncate`, deleted-but-open files

## Ticket

> **INC-2008 · P3 · Monitoring alert**
> `DiskSpaceWarning: /var/log/shopapp 80% used`.
> A logrotate rule for shopapp was added two weeks ago (`/etc/logrotate.d/shopapp`)
> but `app.log` has never been rotated. Also, last week someone changed permissions on
> `/var/log/shopapp` so the deploy group can read logs.
> Make log rotation work - and make sure that after a rotation the app still writes
> to a file you can see. The volume must not fill up again.

## Success criteria

- `logrotate -d /etc/logrotate.d/shopapp` shows no errors
- After a forced rotation, shopapp keeps writing to `/var/log/shopapp/app.log`
- No deleted log file is held open by shopapp
- The rule rotates on size (`size` or `maxsize`), and the volume is below 50%

Check with `sudo ./labctl.sh check m08`.

## Hints

<details><summary>Hint 1 - dry run</summary>

`sudo logrotate -d /etc/logrotate.d/shopapp` (debug = dry run, changes nothing).
Read every `error:` line. What does it say about the directory?
</details>

<details><summary>Hint 2 - force a real rotation, then look</summary>

`sudo logrotate -v -f /etc/logrotate.d/shopapp`, then `curl -s localhost/` a few times.
`ls -l /var/log/shopapp/` - is `app.log` growing? `sudo lsof +L1 /var/log/shopapp`.
</details>

<details><summary>Hint 3 - how does the app find its log?</summary>

The app opens `app.log` once at start and keeps the file descriptor. After `create`
renames the file, where do new lines go? After `compress` deletes the renamed file?
Look up `copytruncate` and `postrotate` in `man logrotate`. How much free space does
`copytruncate` need for a 190 MB file?
</details>

## What you should learn

- `logrotate -d` is the first tool; logrotate refuses insecure (group/world-writable) dirs unless you set `su`.
- A renamed file keeps its inode - processes keep writing to it.
- Rotation strategies: app reopens log on signal (`postrotate` + reload), or `copytruncate`, or restart.
- `compress` without `delaycompress` + an app that keeps the fd = deleted-but-open file (lab M01 again).

Solution: [SOLUTION.md](SOLUTION.md)
