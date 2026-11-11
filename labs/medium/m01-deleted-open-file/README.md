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
