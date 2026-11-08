# Data Files

Rules for Odoo data files — only the decisions an agent cannot infer
from Odoo source code, because the source itself is inconsistent. Everything
else (file formats, CSV conventions, demo data placement) follows standard
Odoo practice: check existing modules when unsure.

## `noupdate` policy

- Wrap in `<data noupdate="1">` the records users are expected to own in
  production: record rules, sequences, crons, operational defaults. An
  upgrade must never reset user-maintained or system-maintained values.
- Keep code-owned records updateable (no noupdate): activities, server
  actions shipped as features — upgrades must be able to deliver
  improvements to them.
- mail templates: it depends, better to ask the user
- `forcecreate` (defaults to `true` in noupdate mode) recreates a record
  the user deleted; set `forcecreate="false"` to respect deletions — rare,
  only for records users may legitimately remove.
- Never rename the xml_id of a noupdate record in the data file alone:
  existing installs keep the old external id and gain a duplicate on
  update. Moving a noupdate record to another module is the exception —
  it requires re-attribution from the receiving module, before its data
  files load; see `migration-scripts.md`.

## Init hooks and migration scripts

- `post_init_hook` (runs after data loading): use it for records data
  files cannot express — per-company creation loops, values computed from
  other modules' state, ORM operations across modules.
- `pre_init_hook` (before loading): conditionally skip heavy data or
  verify prerequisites.
- `migrations/{module_version}/{pre,post}-migrate.py`: used when the module
  is already installed in a database to migrate existing data. Scripts run
  for each version step between the installed version and the target.
- Selection rule: hooks and migration scripts are mutually exclusive per
  database. `{pre,post}_init_hook` run only when the module is *installed*
  (absent from the database); migration scripts run only when it is
  *updated* (already installed, version bumped).
- Unknown installation status (e.g. an OCA module release must apply the
  same setup to fresh installs and existing databases): implement the
  setup once in a shared function, called from both the hook and the
  migration script on the same side of the data load
  (`{pre,post}_init_hook` with its `{pre,post}-migrate.py` counterpart).
  The hook functions live in a `hooks.py` at module root, imported as
  functions from `__init__.py` (`from .hooks import pre_init_hook` —
  manifest hook names resolve as package attributes, so importing the
  module alone is not enough); keep
  the shared code in `models/` only when the business code also uses it
  — not only the migration. Make the function idempotent — guard on
  existing records/parameters so databases in any state converge to the
  same result.
- Reusing hook code from a migration script: scripts always receive
  `(cr, version)` while hooks receive `env` (since 17.0 — `(cr, ...)`
  before, see `versions/17.0.md`) — build an env with
  `api.Environment(cr, SUPERUSER_ID, {})` to call the same shared
  function.
- Use `openupgradelib` (`pip install openupgradelib`, then
  `from openupgradelib import openupgrade`) for data work in hooks and
  migration scripts — renames, value mapping, safe deletions. It is a
  pip-level tool, never a manifest dependency, and does not belong in
  business code. Patterns: see `migration-scripts.md`.
