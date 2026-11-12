# M01 - "I deleted the file but the disk is still full"

**Level:** Medium · **Time:** 20 min · **Skills:** inodes vs. names, open file handles, lsof, /proc

## Ticket

> **INC-2001 · P2**
> Disk alert on `/var/log/shopapp` (85%+). The on-call engineer found a 200 MB
> `shipper-spool.log` and ran `rm` on it. The alert did **not** clear.
> `du` shows the directory is almost empty but `df` still shows it full.
> Free the space. The `log-shipper` service must keep running.

## Success criteria

- `/var/log/shopapp` below 50%
- No process holds a deleted spool file
- `log-shipper` is still active

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

### lsof - who has this file open?

```bash
lsof                                  # 1. every open file of every process (huge)
lsof /var/log/syslog                  # 2. only processes that have THIS file open
lsof -p 1234                          # 3. everything process 1234 has open
lsof +L1                              # 4. open files with link count < 1 = deleted but still open
lsof -nP +L1 /var/log                 # 5. -n/-P = no DNS / port-name lookups (faster); limit to one filesystem
```

### /proc - the kernel's view of a process

```bash
cat /proc/self/status | head                    # 1. 'self' = the cat process itself
ls /proc/self/fd                                # 2. its open file descriptors
ls -l /proc/self/fd                             # 3. -l shows what each fd points to
ls /proc/1234/fd | wc -l                        # 4. how many fds does PID 1234 have?
grep 'open files' /proc/1234/limits             # 5. its fd limit
PID=$(systemctl show -p MainPID --value nginx)  # 6. get a service's PID into a variable
sudo ls /proc/$PID/fd | wc -l                   # 7. now the same check without typing the number
```

## Hints

<details><summary>Hint 1 - df vs du</summary>

`du` adds up file *names* it can see in directories. `df` asks the filesystem
how many blocks are in use. When they disagree a lot, blocks are used by
something without a name.
</details>

<details><summary>Hint 2 - find deleted but open files</summary>

`sudo lsof +L1` lists open files with link count 0 (deleted). Add `-nP` for speed.
Or: `sudo find /proc/*/fd -lname '*(deleted)' -printf '%p -> %l\n' 2>/dev/null`.
</details>

<details><summary>Hint 3 - two ways to free it</summary>

A) Restart the process that holds it (it closes the fd).
B) If you cannot restart, truncate through `/proc`: `: > /proc/<PID>/fd/<FD>`.
</details>

## What you should learn

- A file is an **inode**. `rm` only removes a **name**. Blocks are freed when the
  last name is gone **and** the last open fd is closed.
- `df` vs. `du` mismatch -> think deleted-open files (or files hidden under a mount point).
- Safe log cleanup on a live system: `truncate -s 0 file` (or `: > file`), not `rm`.

Solution: [SOLUTION.md](SOLUTION.md)
