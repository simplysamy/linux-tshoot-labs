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
