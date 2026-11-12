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

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### logrotate - test a rule safely

```bash
cat /etc/logrotate.d/nginx                      # 1. read an existing rule first
sudo logrotate -d /etc/logrotate.d/nginx        # 2. -d = debug / dry run: prints what it WOULD do, changes nothing
sudo logrotate -v /etc/logrotate.d/nginx        # 3. -v = really run (only if due), verbose
sudo logrotate -vf /etc/logrotate.d/nginx       # 4. -f = force now, even if not due
```

### lsof - who has this file open?

```bash
lsof                                  # 1. every open file of every process (huge)
lsof /var/log/syslog                  # 2. only processes that have THIS file open
lsof -p 1234                          # 3. everything process 1234 has open
lsof +L1                              # 4. open files with link count < 1 = deleted but still open
lsof -nP +L1 /var/log                 # 5. -n/-P = no DNS / port-name lookups (faster); limit to one filesystem
```

### ls -lh / ls -ld - sizes and directory modes

```bash
ls -lh /var/log/shopapp/             # 1. file sizes in human units
ls -ld /var/log/shopapp              # 2. the DIRECTORY's own mode and owner
```

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
