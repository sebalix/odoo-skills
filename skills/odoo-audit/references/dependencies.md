# External and new dependency readiness

Optional appendix for a project split across repositories. Use it when
the installed module set contains external modules (OCA/third-party) or
when target-version manifests add dependencies that are not installed.

The inventory CSV remains the source of truth: this appendix aggregates
its external and new-dependency rows and explains the migration gate.

## Inputs

- The installed external modules (from the installed list/instance
  export). They are inventory rows with no module report.
- New non-core dependencies introduced by target-version manifests,
  found by the recursive scan in `module-inventory.md`; they are
  inventory rows with `comment = New - required by module X`.
- Availability/installability and migration PRs from `mca.md` or the
  GitHub fallback.

## Summary

```text
| 18.0 | 19.0 | 20.0 | Installed external modules |
|---|---|---|---|
| 1 | 1 | 1 | ... |
| 1 | 1 | 0 | ... |
| 0 | 0 | 0 | ... |

- 20.0 migrated: X / N
- 19.0 migrated: X / N
- 18.0 migrated: X / N
- Not migrated on any target version: X / N
- Replaced (no port needed): X / N
- Renamed (follow successor): X / N
- New dependencies required by target versions: X (of which not migrated: Y)
```

Keep installed external modules and new dependencies as separate
denominators; do not merge them into one misleading count.

## Tables

### Direct project dependencies that block the target

```text
| Dependency | Used by | 18.0 | 19.0 | 20.0 | PR | Upstream |
|---|---|---|---|---|---|---|
```

### Installed external modules

```text
| Module | Origin / upstream | 18.0 | 19.0 | 20.0 | PR | Status |
|---|---|---|---|---|---|---|
```

### New dependencies required by target versions

```text
| Module | Required by | Origin / upstream | 18.0 | 19.0 | 20.0 | PR | Status |
|---|---|---|---|---|---|---|---|
```

### Unknown / not scanned

List third-party modules absent from the scanned repositories. Their `0`
is **unknown**, not evidence of absence; the comment says so.

## Rules

- `1` = present and installable (migrated); `0` = absent or not migrated
  (`installable: False` is normal and not a separate finding).
- A renamed module follows its successor's availability; a replaced
  module stays `0` with `replaced by ...` and needs no port.
- `PR` is the last open (or closed-unmerged) migration PR for a version
  above the highest available one, formatted `<version>: <url>`; merged
  PRs and PRs for available versions are excluded.
- New dependencies: non-core only unless the user asks otherwise; add
  them recursively from target manifests, skip the existing installed
  tree, and merge multiple requirers into `modules X, Y`.
- No module reports for external/new dependency rows unless the
  dependency is project-owned and on disk.
- Keep the appendix tool-agnostic: no MCA/tool names, cite upstream
  module, version and URL.

## Port gate

The appendix feeds the global report's dependency gate:

- installed external modules not migrated on the target;
- new dependencies not migrated on the target;
- renamed/replaced modules that need a dependency switch;
- unknown modules to verify upstream.

These are additional migration work; do not hide them in the per-module
custom-code effort. Estimate upstream/third-party port work separately.
