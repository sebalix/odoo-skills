# Odoo version migration — module checks

These patterns apply when migrating a module to a new Odoo version
(e.g. 18.0 → 20.0). The mechanics shared with same-version refactorings
— writing migration scripts, moving records between modules, website
COW views, and their verification — live in `migration-scripts.md`; the
per-version framework deltas live in `versions/<X>.md`.

## Module checks

| Check | Old | New |
|-------|-----|-----|
| Manifest file | `__openerp__.py` | `__manifest__.py` |
| Manifest flag | `installable: False` | `installable: True` |
| XML data files | `<data noupdate="0">` | `<data>` — the wrapper is useless |
| Old migration scripts | kept under `migrations/` | not carried over to the new version; write new scripts for the migration itself (see `migration-scripts.md`) |
