# M07 - Hundreds of `<defunct>` processes

**Level:** Medium · **Time:** 25 min · **Skills:** process states, zombies, parent/child, `TasksMax`, why `kill -9` does nothing

## Ticket

> **INC-2007 · P2**
> `queue-dispatcher.service` stopped processing jobs. Its log says
> `fork failed: [Errno 11] Resource temporarily unavailable`.
> `ps` shows ~150 `[python3] <defunct>` processes. The night shift ran
> `kill -9` on them - nothing happened.
> Get the dispatcher processing jobs again. Do **not** raise the unit's `TasksMax` - it
> protects the host from runaway forks.

## Success criteria

- queue-dispatcher is running and dispatching jobs
- No zombie children pile up under it
- `TasksMax` is still 150

Check with `sudo ./labctl.sh check m07`.

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

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

### pipes - building a one-liner step by step

```bash
ps -eo stat                                   # 1. one column of states
ps -eo stat | grep Z                          # 2. keep lines containing Z
ps -eo stat | grep -c '^Z'                    # 3. -c = count them; ^ = at line start
ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/'     # 4. awk: print lines where column 3 matches Z
watch -n1 'ps -eo stat | grep -c "^Z"'        # 5. watch -n1 = re-run every second, live view
# Rule: build a pipeline one stage at a time, run it after each |, and look at the output.
```

### systemctl show / cat - ask systemd for facts

```bash
systemctl cat nginx                              # 1. the unit file(s) systemd really uses, incl. drop-ins
systemctl show nginx                             # 2. every property (long)
systemctl show -p User nginx                     # 3. -p = just one property
systemctl show -p User -p MainPID nginx          # 4. several
systemctl show -p MainPID --value nginx          # 5. --value = print only the value (for scripts)
```

## Hints

<details><summary>Hint 1 - what is a zombie?</summary>

`ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/'`. State `Z` = the process has already exited.
It is only an entry in the process table, waiting for its **parent** to read its exit status.
</details>

<details><summary>Hint 2 - who must clean up?</summary>

Look at the PPID of the zombies. Which process is it? Only the parent (with `wait()`)
or the parent's death removes zombies. Why can a dead process not be killed?
</details>

<details><summary>Hint 3 - why does the parent not reap?</summary>

`systemctl status queue-dispatcher` shows `Tasks: 150 (limit: 150)`. Zombies count against it.
Read the dispatcher's config file (`systemctl cat` shows how it is started).
</details>

## What you should learn

- Zombies use no CPU or memory, but they use a PID and count against `TasksMax` / `pid_max`.
- You cannot kill a zombie - it is already dead. Fix or restart the **parent**.
- When a parent dies, its children are re-parented to PID 1 (or a subreaper), which reaps them.
- `EAGAIN` from fork/clone = a task/PID limit, not a memory problem.

Solution: [SOLUTION.md](SOLUTION.md)
