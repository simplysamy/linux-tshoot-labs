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

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### df - which filesystem is full?

```bash
df                          # 1. every filesystem, sizes in 1 KB blocks (hard to read)
df -h                       # 2. -h = human units (M, G)
df -h /var/log              # 3. give a path: only the filesystem that holds it
df -i /var/log              # 4. -i = inodes (file *count*) instead of bytes
```

### du - what is using the space?

```bash
du /var/log                          # 1. size of every directory below (1 KB blocks)
du -h /var/log                       # 2. human units
du -sh /var/log                      # 3. -s = one summary line for the whole tree
du -h --max-depth=1 /var/log         # 4. one level deep: a size per child
du -xh --max-depth=1 /var/log        # 5. -x = do not cross into other mounted filesystems
du -xh --max-depth=1 /var/log | sort -h   # 6. pipe to sort -h: biggest ends up last
```

### find - search by name, size, age

```bash
find /var/log                                   # 1. everything below, one path per line
find /var/log -type f                           # 2. only regular files (f); d = directories
find /var/log -type f -name '*.log'             # 3. add a name pattern (quote it!)
find /var/log -type f -size +1M                 # 4. bigger than 1 MB (+ = more than)
find /var/log -type f -mmin +60                 # 5. modified more than 60 minutes ago (-60 = less than)
find /var/log -xdev -type f -size +1M           # 6. -xdev = stay on one filesystem
find /var/log -xdev -type f -size +1M -exec ls -lh {} +   # 7. run a command on all hits ({} = the files)
# find ... -delete deletes. ALWAYS run it first without -delete, count with | wc -l, then add it.
```

### lsof - who has this file open?

```bash
lsof                                  # 1. every open file of every process (huge)
lsof /var/log/syslog                  # 2. only processes that have THIS file open
lsof -p 1234                          # 3. everything process 1234 has open
lsof +L1                              # 4. open files with link count < 1 = deleted but still open
lsof -nP +L1 /var/log                 # 5. -n/-P = no DNS / port-name lookups (faster); limit to one filesystem
```

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
