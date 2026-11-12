# M02 - "No space left on device" but the disk is empty

**Level:** Medium · **Time:** 25 min · **Skills:** inodes, counting files, find with age filters, cron

## Ticket

> **INC-2002 · P1 · Customer facing**
> `curl localhost/health` returns `500 ERROR: [Errno 28] No space left on device`.
> The engineer on shift checked `df -h /srv/shopdata` and says it is only ~15% used,
> so "it must be an app bug". Find the real cause and fix it.
> **Do not delete sessions active in the last 24 hours** - customers would lose their carts.

## Success criteria

- `/srv/shopdata` inode use below 50%
- All live sessions (newer than 24h) kept
- `/health` returns 200
- The root cause is fixed, so it does not come back

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

### du --inodes - where are the many files?

```bash
ls /srv/shopdata/sessions | head                 # 1. look at a few names first
ls -lt /srv/shopdata/sessions | head             # 2. -t = newest first
du --inodes /srv/shopdata                        # 3. count files (inodes) per directory instead of bytes
du --inodes -x /srv/shopdata | sort -n | tail -3 # 4. biggest file-count last
```

## Hints

<details><summary>Hint 1 - two kinds of "space"</summary>

A filesystem can run out of **blocks** (data) or out of **inodes** (one per file/dir).
`df -h` shows blocks. Which flag shows inodes?
</details>

<details><summary>Hint 2 - where are all the files?</summary>

`sudo du --inodes -x /srv/shopdata | sort -n | tail` or
`sudo find /srv/shopdata -xdev -type f | cut -d/ -f1-4 | sort | uniq -c | sort -n`.
</details>

<details><summary>Hint 3 - delete by age, safely</summary>

First **list** and count: `find ... -mmin +1440 | wc -l`. Then change `-print` to `-delete`.
Why did they pile up? Look in `/etc/cron.d/`.
</details>

## What you should learn

- ENOSPC can mean no blocks **or** no inodes. Always run `df -h` **and** `df -i`.
- Millions of tiny files (sessions, cache, mail queue, temp files) eat inodes, not bytes.
- Always dry-run destructive `find`: list -> count -> then `-delete`.
- Fix the cause (the disabled cleanup job), not only the symptom.

Solution: [SOLUTION.md](SOLUTION.md)
