# M06 - Everything is slow, CPU is idle

**Level:** Medium · **Time:** 30 min · **Skills:** memory pressure, swap, `vmstat si/so`, RSS vs. swap per process, sysctl persistence

## Ticket

> **INC-2006 · P2**
> Since the change window for **CHG-552 "batch performance tuning"** the host is very
> sluggish: SSH takes seconds to echo keys, the shop is slow, load average is high.
> `top` shows the CPUs mostly idle. Nobody sees a CPU hog.
> `report-builder.service` (the nightly batch) must keep running - just not like this.

## Success criteria

- The host stops swapping (no steady swap-in/swap-out)
- `report-builder` keeps running with a sane memory footprint (≤ 50% of RAM)
- The swappiness "tuning" from CHG-552 is undone at runtime **and** on disk

Check with `sudo ./labctl.sh check m06`.

## Hints

<details><summary>Hint 1 - CPU idle, load high</summary>

Load counts tasks waiting for CPU **and** tasks waiting in the kernel (I/O, page faults).
`vmstat 1 10` - look at the `si`/`so` (swap in/out) columns and `wa`. `free -m`.
</details>

<details><summary>Hint 2 - who uses the memory?</summary>

`ps -eo pid,user,rss,vsz,cmd --sort=-rss | head`. Swap per process:
`grep VmSwap /proc/*/status | sort -k2 -n | tail`. Add up all workers of the same program.
</details>

<details><summary>Hint 3 - what did CHG-552 change?</summary>

Look at recently changed files: `ls -lt /etc /etc/sysctl.d | head`.
`sysctl vm.swappiness`, and read the report-builder config. Two settings were changed.
</details>

## What you should learn

- Swap thrashing looks like "slow everything, CPU idle". `si`/`so` > 0 every second is the signal.
- `free` "used" is not the story: check **available** and swap activity.
- Size worker pools to RAM: workers × memory per worker must fit with headroom.
- `vm.swappiness` changes *when* the kernel swaps; it does not create memory.
- A runtime `sysctl -w` is lost at reboot; a file in `/etc/sysctl.d/` comes back at boot.

Solution: [SOLUTION.md](SOLUTION.md)
