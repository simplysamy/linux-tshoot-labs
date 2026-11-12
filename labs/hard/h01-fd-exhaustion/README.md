# H01 - App hangs after some traffic, restart "fixes" it

**Level:** Hard · **Time:** 40 min · **Skills:** file descriptors, ulimits, /proc, systemd drop-ins, strace

## Ticket

> **INC-3001 · P1 · Customer facing · recurring**
> Since yesterday shopapp stops answering after a few minutes of traffic.
> nginx returns **504 Gateway Timeout**. CPU of the app goes high while it hangs.
> Restarting shopapp fixes it for a few minutes, then it happens again.
> The team already did 4 restarts today. We need the root cause, not another restart.

## Success criteria

- shopapp survives 300+ requests and stays healthy
- No fd leak (fd count stays low)
- Limits are sane (soft NOFILE >= 1024)

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### curl - talk to a web service

```bash
curl http://localhost/                                   # 1. fetch a page, print the body
curl -s http://localhost/                                # 2. -s = silent (no progress bar)
curl -s -o /dev/null http://localhost/                   # 3. -o /dev/null = throw the body away
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/   # 4. -w = print only the HTTP status code
curl -v http://localhost/                                # 5. -v = verbose: shows connect, headers (debug)
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 5 http://localhost/   # 6. + timing, + give up after 5 s
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

### ps / pgrep / pstree - look at processes

```bash
ps                                         # 1. only your shell
ps -ef                                     # 2. every process, full format (PID, PPID, command)
ps -fp 1234                                # 3. just one PID
ps -eo pid,ppid,user,%cpu,%mem,cmd         # 4. -o = choose your own columns
ps -eo pid,%cpu,cmd --sort=-%cpu | head    # 5. sort by CPU, highest first (- = descending), top 10
pgrep -af nginx                            # 6. find PIDs by name (-a = show full command, -f = match whole command line)
pstree -ps 1234                            # 7. parent chain of one PID: who started it?
```

### strace - see what a process asks the kernel

```bash
strace ls /nonexistent                          # 1. run a command and print every system call
strace -e trace=openat ls /nonexistent          # 2. -e = only these calls (openat = open a file)
sudo strace -p 1234                             # 3. -p = attach to a running process
sudo strace -f -p 1234 -e trace=openat,close    # 4. -f = follow child threads; two call types
sudo strace -f -p 1234 -e trace=openat,close -o /tmp/st.txt   # 5. -o = write to file, then grep it
# openat without a matching close = a file-descriptor leak.
```

### systemctl show / cat - ask systemd for facts

```bash
systemctl cat nginx                              # 1. the unit file(s) systemd really uses, incl. drop-ins
systemctl show nginx                             # 2. every property (long)
systemctl show -p User nginx                     # 3. -p = just one property
systemctl show -p User -p MainPID nginx          # 4. several
systemctl show -p MainPID --value nginx          # 5. --value = print only the value (for scripts)
```

### sed - edit text from the command line

```bash
sed 's/old/new/' file           # 1. print file with the first 'old' on each line replaced (file unchanged)
sed 's/old/new/g' file          # 2. g = every match on the line
sed -n '3p' file                # 3. -n + p = print only line 3
sed '/old/d' file               # 4. d = delete lines that match (still only printed)
sed -i 's/old/new/' file        # 5. -i = edit the file IN PLACE (make a copy first: cp file file.bak)
sed -i 's#/a/b#/c/d#' file      # 6. any delimiter works: # avoids escaping / in paths
```

## Hints

<details><summary>Hint 1 - what does the process see?</summary>

Find the PID: `systemctl show -p MainPID shopapp`. Then count open fds:
`sudo ls /proc/<PID>/fd | wc -l`. Compare to `grep 'open files' /proc/<PID>/limits`.
`journalctl -u shopapp` - search for `Errno`.
</details>

<details><summary>Hint 2 - what are those fds?</summary>

`sudo ls -l /proc/<PID>/fd` or `sudo lsof -p <PID>`. Many fds to the same file = leak.
`sudo strace -f -p <PID> -e trace=openat,accept4` while you send one request.
</details>

<details><summary>Hint 3 - where does the limit come from?</summary>

`systemctl cat shopapp` prints the unit **and every drop-in** with file paths.
`systemctl show -p LimitNOFILE shopapp`. Two changes combined into one outage.
</details>

## What you should learn

- `EMFILE (Errno 24) Too many open files` = per-process fd limit reached.
- `/proc/<PID>/fd` and `/proc/<PID>/limits` show the real state of a running process.
  Your shell's `ulimit -n` does **not** apply to systemd services.
- `systemctl cat` reveals drop-ins in `/etc/systemd/system/<unit>.d/` that override the main unit.
- Two changes can be safe alone and break together. Raising the limit alone only delays a leak.

Solution: [SOLUTION.md](SOLUTION.md)
