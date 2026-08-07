# Duty Board — Rollback & Recovery Runbook

Practical recovery steps for the `duty_board` Frappe app, written from real
incidents. Read the section that matches your situation. When in doubt, the
guiding principle is: **the git history is the source of truth, and a failed
migrate almost never means lost data.**

Environment assumptions used throughout:

- Bench: `~/frappe-bench`
- App path: `~/frappe-bench/apps/duty_board`
- Site: `xlevel.clouderp.one`
- Remote: `github.com/CloudERPng/duty_board.git` (named both `origin` and
  `upstream` — same repo; the branch tracks `upstream/main`)
- Version string lives in `duty_board/__init__.py` as `__version__`.

---

## 0. The one-minute health check

Run this first, always. It tells you what state you're in.

```bash
cd ~/frappe-bench/apps/duty_board
grep __version__ duty_board/__init__.py     # what version is on disk
git status                                   # clean? ahead/behind remote?
git log -1 --oneline                         # last commit
```

- **Working tree clean + up to date with upstream** → you are on a known-good,
  backed-up commit. Any problem is runtime (restart/build), not code loss.
- **Ahead of upstream by N commits** → local work not yet pushed. Back it up:
  `git push upstream main` before doing anything risky.
- **Dirty working tree** → uncommitted edits exist. Decide to keep or discard
  (sections below) before switching versions.

---

## 1. "The last deploy broke the UI / board won't load"

Most breakage is a bad JS/HTML edit or a stale build, not data. Order of
escalation, least destructive first:

### 1a. Rebuild + restart (fixes most "it looks broken" cases)

```bash
cd ~/frappe-bench
bench build --app duty_board
bench restart
bench --site xlevel.clouderp.one clear-website-cache   # if the CLIENT PORTAL is wrong
```

Then hard-refresh the browser (Ctrl/Cmd+Shift+R). A surprising share of
"broken" states are just a cached old bundle.

### 1b. Revert to the previous commit (code is the problem)

If a specific deploy broke something and rebuild didn't fix it:

```bash
cd ~/frappe-bench/apps/duty_board
git log --oneline -10                 # find the last-good commit hash
git revert --no-edit <bad_commit>     # SAFE: makes a NEW commit undoing the bad one
# — or, to jump the working tree back without rewriting history:
git stash                             # park any uncommitted edits first
git checkout <last_good_hash> -- .    # restore files to that commit's state
```

Prefer `git revert` (adds an undo commit, history stays honest) over
`reset --hard` on anything already pushed. After reverting:

```bash
cd ~/frappe-bench && bench build --app duty_board && bench restart
```

### 1c. Discard ALL uncommitted local edits (nuclear, local only)

Only when you are certain the uncommitted changes are the problem and worth
throwing away:

```bash
cd ~/frappe-bench/apps/duty_board
git checkout -- .        # discard tracked-file edits
git clean -fd            # delete untracked files (CAREFUL: removes new files too)
```

This returns you to the last commit. It does **not** touch the database.

---

## 2. "bench migrate failed"

**Read this first, it's the most important lesson from today:** a migrate that
fails **at patch import/registration** (e.g. `ModuleNotFoundError`, or a patch
listed in `patches.txt` whose file is missing) fails **before any data is
written**. No data is harmed. The backfill/patch code is idempotent. You fix
the cause and re-run — the migrate resumes cleanly.

### 2a. Migrate fails with `ModuleNotFoundError: duty_board.patches...`

Cause: a patch is registered in `patches.txt` but its `.py` file isn't on the
server, or `duty_board/patches/__init__.py` is missing.

```bash
cd ~/frappe-bench/apps/duty_board
ls duty_board/patches/                       # is the referenced file here?
ls duty_board/patches/__init__.py            # must exist (even if empty)
grep -n "patches" ../duty_board/duty_board/patches.txt 2>/dev/null || \
  cat duty_board/patches.txt                 # what's registered
```

Fix options:
- If `__init__.py` is missing: `touch duty_board/patches/__init__.py`
- If the patch FILE is missing but registered: either restore the file
  (it should be committed — `git checkout upstream/main -- duty_board/patches/<file>.py`)
  or remove its line from `patches.txt` if the patch is obsolete.

Then re-run — it resumes:

```bash
cd ~/frappe-bench && bench --site xlevel.clouderp.one migrate
```

> **Root-cause prevention (do this, it bit us repeatedly):** patch scripts and
> `patches/*.py` files MUST be committed to git. When they were only staged as
> downloads and never committed, they went missing on the server and crashed
> migrate. If you add a patch, `git add` it in the same commit.

### 2b. Migrate fails inside a patch's data logic

Rare here (our patches are simple/idempotent), but if it happens: read the
traceback, fix the patch code, re-run migrate. Because patches are idempotent
and Frappe records which patches completed, re-running only executes the ones
that haven't succeeded yet.

### 2c. You need to un-register a patch that shouldn't run

```bash
cd ~/frappe-bench/apps/duty_board
# remove the offending line from patches.txt, then:
cd ~/frappe-bench && bench --site xlevel.clouderp.one migrate
```

---

## 3. "A schema change (new field) is causing errors"

New fields are added via doctype JSON; `bench migrate` creates the columns.
Our added fields (e.g. `baseline_date`, `baselined_on`, `room`, `project`,
`baseline_date`) are **nullable with no backfill** — null is a valid, correct
state. So a schema issue is almost never "bad data"; it's usually a code path
referencing a field before migrate created the column.

Fix: ensure migrate ran (`bench --site xlevel.clouderp.one migrate`), then
rebuild + restart. If you reverted code that expected a column that now exists,
that's harmless — an extra column bothers nothing.

To confirm a column exists:

```bash
bench --site xlevel.clouderp.one mariadb -e \
  "SHOW COLUMNS FROM \`tabDuty Milestone\` LIKE 'baseline_date';"
```

---

## 4. Full rollback to a known-good release

When you want the entire app back to a specific version:

```bash
cd ~/frappe-bench/apps/duty_board
git fetch upstream
git log --oneline -20                          # find the target commit
git stash                                       # park local edits if any

# Safe path (keeps history): revert forward to the good state
git revert --no-edit <first_bad>..<HEAD>       # undo a RANGE of commits

# — OR hard path (LOCAL ONLY, not yet pushed): move the branch back
git reset --hard <good_hash>                   # DANGER: discards commits after it

cd ~/frappe-bench
bench --site xlevel.clouderp.one migrate       # re-sync schema to the code
bench build --app duty_board
bench restart
```

**Rule:** never `reset --hard` a commit that's already on the remote and that
others may have pulled. Use `revert` there. `reset --hard` is only safe for
local commits nobody else has seen.

---

## 5. Database safety notes (learned the hard way)

- **MariaDB safe-update mode** blocks bare `DELETE`/`UPDATE` (even
  `WHERE name IS NOT NULL`). Prefix with `SET SQL_SAFE_UPDATES=0;` in the same
  `-e` statement, or use `TRUNCATE` for a full-table clear.
- **Before any destructive SQL, SELECT first.** Run the `SELECT` form of your
  `WHERE` clause and eyeball the rows. A `DELETE FROM \`tabDuty Project Task\``
  with no `WHERE` wipes every project's tasks — scope it
  (`WHERE project IN (...)`) and verify the count before deleting.
- **Child tables orphan.** Deleting a parent row (e.g. a `Duty Project Task`)
  leaves its child rows (`Duty Project Subtask`, keyed by `parent`) dangling.
  Delete children first via a JOIN on the parent, then the parents.
- **Take a backup before big data operations:**
  `bench --site xlevel.clouderp.one backup` (writes to `sites/.../private/backups`).

---

## 6. Deploy discipline (prevents most of the above)

The checklist that keeps rollbacks rare:

1. `grep __version__` **before** applying a patch (confirm the expected
   predecessor version) **and after** (confirm it advanced — if the version
   didn't move, the patch didn't run).
2. Apply patch → `bench migrate` (only if the patch changed a doctype) →
   `bench build --app duty_board` → `bench restart`.
3. `git add -A && git commit` **including any patch/apply scripts** →
   `git push upstream main`.
4. `git status` → confirm **"up to date"** and **"working tree clean."**
   Those two phrases mean the work is safely off this disk and on GitHub.

Local commits are **not** a backup — they live on the same disk as everything
else. The `push` is the backup. Push often.

---

_Last updated: keep this current when recovery steps change._
