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
