---
name: odoo-review-oca-migration
description: Review OCA (Odoo Community Association) migration/port pull requests from a https://github.com/OCA/<repo>/pull/<number> URL — [MIG] full-module migrations and [FW]/[PORT]/[BACKPORT] commit ports made with git format-patch/cherry-pick. Verifies each ported commit against its source-branch original, checks adaptations against the target version's migration guide, audits completeness (missing/blacklisted commits), and runs the full OCA migration checklist (manifest version, copyright/authors, migrations folder, pre-commit, tests, CREDITS, CI). Produces an English report plus a paste-ready review comment. Use ONLY when the user asks to review an OCA migration/port PR or supplies such a URL, not to author one.
compatibility: Requires the odoo-knowledge skill. Uses the GitHub CLI when available; ships fallbacks otherwise.
metadata:
  requires-skills: odoo-knowledge
---

# Review an OCA migration / port pull request

A user gives you an OCA PR URL such as
`https://github.com/OCA/server-tools/pull/3632`. The PR ports commits
(a whole module's history, or individual fixes/features) from one Odoo
version branch to another one with `git format-patch` + `git am` or
`git cherry-pick`. Ported commits must stay faithful to the originals:
same subject and author, content changed only where the target version
requires it. SHAs will differ.

**Hard rules**

- Read-only review: never push, comment, review, merge, or close anything on
  GitHub. Never run `git am` or `git cherry-pick`. Deliver the report to the
  user; they post it.
- Work in a throwaway clone under `/tmp/odoo-review-oca-migration/`.
  Never touch the user's local checkouts.
- Prefer `gh` (check `gh auth status`) for PR metadata, files, commits, CI,
  and existing review comments. If `gh` is unavailable or unauthenticated,
  fall back to the unauthenticated REST API (60 req/h) via curl/webfetch, or
  to plain git. Git stays the source of truth for history facts (patch-ids,
  tree diffs).
- Paths in this skill (`scripts/`, `references/`) are relative to this
  skill's directory.

## 0. Fetch the PR

Required: the PR URL (ask if missing). Optional: the source branch if the PR
body is unclear. Parse `REPO` and `N` from the URL, then:

```bash
REPO=<repo>; N=<number>
WORK="/tmp/odoo-review-oca-migration/$REPO-$N"
rm -rf "$WORK"; mkdir -p /tmp/odoo-review-oca-migration
git clone --quiet "https://github.com/OCA/$REPO" "$WORK"
git -C "$WORK" fetch --quiet origin "refs/pull/$N/head:pr-$N"
PR_SHA=$(git -C "$WORK" rev-parse "pr-$N")
```

## 1. PR metadata, CI, and existing reviews

Prefer `gh` (authenticated). It accepts the full URL, and its commit list is
authoritative — GitHub's own view of the PR, which excludes unrelated commits
that merely sit on the contributor's branch. If `gh auth status` fails, use
the fallbacks in `references/gh-fallbacks.md` instead.

```bash
gh pr view "$N" --repo "OCA/$REPO" \
  --json number,title,author,state,isDraft,mergedAt,baseRefName,headRefName,headRepositoryOwner,headRepository,headRefOid,changedFiles,body,comments,reviews \
  --jq '{title,author:.author.login,state,isDraft,mergedAt,base:.baseRefName,head:.headRefName,headRepo:(.headRepositoryOwner.login+"/"+.headRepository.name),headRefOid,changedFiles,body,ncomments:(.comments|length),nreviews:(.reviews|length),reviewers:[.reviews[].author.login]}'

# CI: exits non-zero when a check fails or none are reported — read the output
gh pr checks "$N" --repo "OCA/$REPO" || true

# Existing discussion: do not repeat maintainers' points in the report
gh pr view "$N" --repo "OCA/$REPO" --json comments,reviews \
  --jq '([.reviews[] | "REVIEW by \(.author.login) [\(.state)]: \(.body // "")"] + [.comments[] | "COMMENT by \(.author.login): \(.body)"]) | .[]'
```

Confirm the fetched ref matches the GitHub head (a mismatch means the branch
was force-pushed between the clone and now; re-fetch the ref and restart):

```bash
git -C "$WORK" rev-parse "pr-$N"   # compare with headRefOid above
```

## 2. Classify and scope the PR

- `TARGET` = the base branch from section 1 (e.g. `19.0`).
- `SOURCE` = version branch the commits come from, usually the highest
  version branch below TARGET:
  `git -C "$WORK" branch -r | grep -E 'origin/[0-9]+\.[0-9]+$'`.
  Confirm with the PR body (`port from 18.0`, `[FW]`, cherry-pick trailers)
  and by locating originals in section 3. Multi-version jumps mean every
  intermediate migration guide applies.
- `MODULE` = addon path(s) touched:

```bash
gh pr diff "$N" --repo "OCA/$REPO" --name-only | cut -d/ -f1 | sort -u
```

- If the module was renamed, use the old path on SOURCE and the new path on
  TARGET.

Load the `odoo-knowledge` skill and read its version references: the
Old → New delta for TARGET (`references/versions/<TARGET>.md`), plus every
intermediate version between SOURCE and TARGET. These delta tables are the
authority for framework changes when justifying adaptations (section 3) and
checking the checklist (section 5); the OCA guides fetched in section 5
remain the authority for OCA process.

Authoritative PR commit list, oldest first (works for open and merged PRs):

```bash
gh pr view "$N" --repo "OCA/$REPO" --json commits \
  --jq '.commits[] | .oid + " " + .messageHeadline' > /tmp/odoo-review-oca-migration/pr-commits.txt
cat /tmp/odoo-review-oca-migration/pr-commits.txt
```

For very large PRs, page the REST endpoint instead:

```bash
gh api --paginate "repos/OCA/$REPO/pulls/$N/commits?per_page=100" \
  --jq '.[] | .sha + " " + (.commit.message | split("\n")[0])' > /tmp/odoo-review-oca-migration/pr-commits.txt
```

Fallback without `gh`: read `references/gh-fallbacks.md` for the PR
commit list.

Flag commits that do not belong to `MODULE`/`SOURCE` as out-of-scope.

## 3. Commit fidelity audit

For each PR commit `$C`, locate its original on `origin/$SOURCE`:

1. Cherry-pick trailer:
   `git -C "$WORK" show -s --format=%B "$C" | grep -oE 'cherry picked from commit [0-9a-f]{7,40}'`
2. Subject match (subjects are normally preserved):
   `git -C "$WORK" log --no-merges --format='%H %s' "origin/$SOURCE" -- "$SOURCE_MODULE" | grep -F -- "<subject>"`
3. Patch-id match — strongest evidence of content equivalence:

```bash
# patch-ids of source-branch commits touching the module
git -C "$WORK" log --no-merges --format=%H "origin/$SOURCE" -- "$SOURCE_MODULE" \
  | scripts/patch-ids.sh "$WORK" > /tmp/odoo-review-oca-migration/src-pids.txt

# patch-ids of the PR commits listed in section 2 (skip out-of-scope ones)
cut -d' ' -f1 /tmp/odoo-review-oca-migration/pr-commits.txt \
  | scripts/patch-ids.sh "$WORK" > /tmp/odoo-review-oca-migration/pr-pids.txt

# identical pairs: <patch-id> <source-sha> <pr-sha>
join -j1 <(sort /tmp/odoo-review-oca-migration/src-pids.txt) <(sort /tmp/odoo-review-oca-migration/pr-pids.txt)
```

Classify each PR commit:

- **identical** — same patch-id; author (`git show -s --format='%an <%ae>'`)
  and subject unchanged.
- **adapted (justified)** — differs only where the target version requires.
  Pair it with its original and inspect the net difference (this is more
  reliable than `git range-diff`):
  `git -C "$WORK" diff "$ORIG:$SOURCE_MODULE" "$PORTED:$MODULE" --stat`
  and the full diff when small. Justify each hunk against the odoo-knowledge
  Old → New delta for TARGET and the intermediate versions, cross-checked
  with the fetched migration guide; anything neither explains is a finding.
- **unexplained** — adapted beyond documented framework changes, or no
  original found, or author changed.

Keep the original author unchanged; the committer may be the porter.

Exclude administrative commits from fidelity (list them, do not flag):
`[UPD] README.rst`, `[UPD] *.pot`, `[UPD] addons table`, `[BOT] ...`,
`Added translation using Weblate ...`, `Translated using Weblate ...`.
Review the `[IMP] <module>: pre-commit auto fixes` commit for formatting
only — it must be a separate commit.

For a full-module migration, check overall tree parity at PR head vs SOURCE;
the remaining differences should all be explainable adaptations:

```bash
git -C "$WORK" diff "pr-$N:$MODULE" "origin/$SOURCE:$MODULE" --stat
```

## 4. Completeness audit

Did the PR port everything intended? List source-branch module commits:

```bash
git -C "$WORK" log --no-merges --oneline "origin/$TARGET..origin/$SOURCE" -- "$MODULE"
```

For each source commit, check whether its patch-id exists among target
module commits (same technique as section 3). Check the oca-port blacklist
for deliberate skips before flagging anything. oca-port stores the blacklist
on the **target** branch of the port, and porters may add entries in the PR
itself, so check both:

```bash
git -C "$WORK" show "origin/$TARGET:.oca/oca-port/blacklist/$MODULE.json" 2>/dev/null
git -C "$WORK" show "pr-$N:.oca/oca-port/blacklist/$MODULE.json" 2>/dev/null
```

Format: `{"pull_requests": {"OCA/<repo>#<n>": "<reason>"}}` (older entries may
key by bare PR number). Blacklisted PRs are intentionally unported — mention
them as skipped, do not flag them. If `oca-port` is installed,
`oca-port --dry-run --verbose origin/$SOURCE origin/$TARGET $MODULE`
is a useful cross-check, but never depend on it.

## 5. OCA checklist

Fetch the live guide(s) for the target version — do not rely on memory, the
guide changes between versions:

- `https://github.com/OCA/maintainer-tools/wiki/Migration-to-version-<TARGET_MAJOR>.0`
  (e.g. `.../Migration-to-version-19.0`); check every intermediate guide for
  multi-version jumps.
- Conventions: `https://github.com/OCA/maintainer-tools/wiki/Conventions`

Then verify:

- [ ] `__manifest__.py` version bumped to `<TARGET>.0.x.y.z`.
- [ ] Copyright years unchanged and original authors untouched (explicit
      "tasks NOT to do" in the migration guide).
- [ ] License unchanged (OCA FAQ: license cannot change on a port).
- [ ] Old `migrations/` scripts removed for a version migration; any new
      script justified.
- [ ] Framework changes required by the target version applied where
      relevant — verify against the odoo-knowledge Old → New delta tables
      for TARGET (and intermediate versions), cross-checked with the
      fetched guide.
- [ ] `[MIG] <module>: Migration to <TARGET>` commit present for full
      migrations.
- [ ] Separate pre-commit auto-fix commit where the guide's process expects
      one.
- [ ] Tests present/extended and compliant with the odoo-knowledge testing
      conventions (`references/testing.md`) and guide-specific rules (e.g.
      `tracking_disable`, demo-data independence); the guide wins on
      migration-specific rules.
- [ ] `CREDITS.rst` cleaned of past financed migrations.
- [ ] No unrelated refactoring bundled into the port.
- [ ] PR title matches `[<TARGET>][MIG|FW|PORT|BACKPORT] <module>: ...`;
      correct base branch; draft status noted.
- [ ] CI checks from section 1 pass; list failures.
- [ ] Commit author preserved on ported commits.

## 6. Report

Write in English. Produce the report following
`references/report-template.md` — including the paste-ready review comment
and the uncertainties section.

## Edge cases

- **Already merged PR**: head may be an ancestor of TARGET; use the API or
  merge commit (section 2) for commits/files, and still review fidelity.
- **Force-pushed branch**: re-fetch the PR ref right before concluding and
  report the head SHA the review applies to.
- **Squashed or rewritten ports**: no 1:1 commit mapping — rely on patch-id
  sets and module tree parity; say so explicitly.
- **Multiple modules**: repeat sections 3–5 per module.
- **Module renamed**: compare `$SOURCE:<old>/` with `$TARGET:<new>/`.
- **New module (absent on SOURCE)**: it is an `[ADD]`; review it against OCA
  module standards and the odoo-knowledge references (start with
  `references/module-structure.md`), not fidelity.
- State clearly anything that could not be verified.
