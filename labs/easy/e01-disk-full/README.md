# E01 - Log volume full

**Level:** Easy · **Time:** 15 min · **Skills:** disk usage, finding big files, safe cleanup

## Ticket

> **INC-1001 · P3 · Monitoring alert**
> `DiskSpaceCritical: /var/log/shopapp is 100% full on tshoot-lab`
> The app team also says shopapp's log (`/var/log/shopapp/app.log`) stopped
> getting new lines a few minutes ago. The site still loads.
> Please free up space and make sure the app logs again. Do not delete
> `app.log` itself - the audit team needs it.

## Success criteria

- `/var/log/shopapp` below 80% used
- shopapp writes new lines into `app.log` again
- `app.log` still exists

Check with `sudo ./labctl.sh check e01`.

## Hints

<details><summary>Hint 1 - confirm the alert</summary>

Do not trust the alert, confirm it. Which command shows usage per filesystem?
`df -h`. Is `/var/log/shopapp` its own filesystem?
</details>

<details><summary>Hint 2 - find what is big</summary>

`du -xh --max-depth=1 /var/log/shopapp | sort -h` shows which directory is big.
`find /var/log/shopapp -xdev -type f -size +20M -exec ls -lh {} +` shows big files.
</details>

<details><summary>Hint 3 - before you delete</summary>

Look inside the big file first (`tail -n 3`). Is anything still writing to it?
`lsof /var/log/shopapp/<file>` - if a process holds it open, deleting it will NOT
free space (that is lab M01).
</details>

## What you should learn

- `df` tells you *which filesystem* is full; `du` / `find` tell you *what* is filling it.
- `-x` / `-xdev` keeps `du` and `find` on one filesystem - important when other
  volumes are mounted underneath.
- Always look at a file and check who writes it before you delete it.
- Logs that grow without limit need `logrotate` and a monitoring alert at 80%, not 100%.

Solution: [SOLUTION.md](SOLUTION.md) - try for 15 minutes first.
