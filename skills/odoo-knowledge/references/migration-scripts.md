# Migration scripts and record moves

Rules for scripts that upgrade installed databases in place: the
`migrations/` folder of a module, which runs whenever the module version is
bumped past the installed one. Two cases use the same patterns: refactoring
modules within one Odoo version (e.g. moving records between modules), and
migrating a module to a new Odoo version. The version-specific module checks
live in `migrations/common-patterns.md`, the framework deltas in
`versions/<X>.md`; everything else follows the openupgradelib documentation
and the OCA migration guides.

## openupgradelib

`openupgradelib` is the OCA support library for migration scripts and
hooks (`pip install openupgradelib`, then
`from openupgradelib import openupgrade`). Pip-level tool: never a
manifest dependency, never business code.

- `@openupgrade.migrate()` decorator on `def migrate(env, version)`:
  bridges `cr` to an env, wraps the run in a savepoint, logs failures
  with script and module context.
- Renames: `rename_xmlids(cr, [...])`, `rename_fields(env, [...])`,
  `rename_columns`, `rename_tables`, `rename_models`,
  `rename_field_references`. Read a value written before a field rename
  through `openupgrade.get_legacy_name('<field>')`.
- Module refactors: `update_module_names`,
  `update_module_moved_fields`, `update_module_moved_models`.
- Data operations: `logged_query(cr, sql, args)` — the replacement for
  raw `cr.execute` in scripts (logs the query and affected rows);
  `load_data` (load XML data during the migration), `map_values`,
  `set_defaults`, `copy_columns`.
- Records: `delete_records_safely_by_xml_id` (removes the record and
  everything pointing at it), `safe_unlink`, `chunked`,
  `update_field_multilang`.
- Website COW views: `cow_templates_mark_if_equal_to_upstream` in the
  pre-migration + `cow_templates_replicate_upstream` in the
  post-migration — keep website-specific qweb copies in sync when
  their generic view changes or moves (see "Moving website views").
- Schema introspection: `openupgradelib.openupgrade_tools`
  (`table_exists`, `column_exists`, ...). Version-specific helpers live
  in `openupgradelib.openupgrade_140` … `openupgrade_180`.

## Moving records between modules

When records (fields, models, access rights, mail templates, views...)
move from one module to another, re-attribute their XML ids so the
upgrade reuses the existing records instead of dropping columns/tables
and creating duplicates.

**Recipe** — all receiver-side (see "Why receiver-side" below):

1. Inventory the moved XML ids from the production database if any
   (`ir_model_data` rows owned by the sending module), not from the
   data files: reflection ids (`model_*`, `field_*`, `selection__*`)
   and ACLs declared in CSV never appear in XML files.
2. Re-attribute before the receiving module loads its data files — in
   its `pre-migration` script when the module is already installed, or
   its `pre_init_hook` when it is not (migrations never run at
   install):

   ```python
   # receiving_module/migrations/<version>/pre-migrate.py
   from openupgradelib import openupgrade

   @openupgrade.migrate()
   def migrate(env, version):
       openupgrade.rename_xmlids(env.cr, [
           ("sending_module.xml_id", "receiving_module.xml_id"),
       ])
   ```

3. Let the receiver's data files define the records, and encode the
   production state in them before deploying: at install, all data
   files load (`mode='init'`), and re-attributed records get their
   file-defined fields reset to the file values. Diff each moved record
   against the receiver's data file and encode the production manual
   overrides there.

4. Optionally keep fallback entries in the sending module's migration:
   harmless on regular upgrades (the receiver already renamed the rows,
   both branches no-op), useful on selective updates (`-u sender`
   alone applies the plain renames).

**Why receiver-side**

- The sending module loads after its dependencies, so its own migration
  runs too late: the receiver's data files have already re-created the
  records — the duplicate exists.
- Data records (views, access rights, mail templates...) are re-created
  by the data files: only a receiver-side rename avoids duplicates.
- Reflection-managed records (`ir.model`, `ir.model.fields`) are reused
  by the model reflection: a delete-stale-if-fresh from the sending
  module works, but the reflection then creates a fresh xmlid row and
  the original `create_date` is lost. Rename receiver-side to keep the
  provenance.
- `noupdate="1"` records are safe across any load order (`_process_end`
  never garbage-collects them) but still require re-attribution — the
  receiver's data load would otherwise create a duplicate.

**Process rules**

- Write the scripts for the production database state only: a
  development database's state cannot be guaranteed — recreate it from
  the production dump instead of coding for its intermediate states.
  `rename_xmlids` skips missing sources, so re-runs are safe.
- A migration folder runs only when
  `installed_version < folder_version <= manifest_version`: place it at
  the target version only when that version is unreleased; when it
  already reached production, bump the manifest and use the new
  version.

## Moving website views (COW copies)

Apply this when a moved qweb view has website-specific copies: rows in
`ir_ui_view` with `website_id` set and the generic view's `key`. COW
copies have no `ir.model.data` entry, so `rename_xmlids` cannot touch
them. Left alone they keep the old key and old arch; the update then
creates a fresh specific copy of the renamed view and both copies apply
at the same priority — pages crash or misbehave at render time.

Clean flow, receiver-side (see Moving records between modules), in the
receiving module's `pre-migration`:

1. Rename the generic view's xmlid (`rename_xmlids`). The stored `key`
   is not recomputed: it keeps the old value, which is what shields the
   copies during the data load.
2. Mark the identical copies:
   `openupgrade.cow_templates_mark_if_equal_to_upstream(env.cr)` marks
   every specific copy whose `arch_db` equals its generic's. It matches
   copies to their generic by `key`, so run it now, while the copies
   still carry the old key, before any re-keying.
3. Re-key every copy — customized ones too — to the key of the
   receiving module's xmlid for the generic view:

   ```sql
   UPDATE ir_ui_view
   SET key = '<new_key>' WHERE key = '<old_key>'
     AND website_id IS NOT NULL;
   ```

4. In `post-migration`, run
   `openupgrade.cow_templates_replicate_upstream(env.cr)`: it resets the
   marked copies' `arch_db`/`inherit_id` from the updated generic (raw
   SQL, no view validation involved).

Why it works: the generic's stale stored key shields the copies from
load-time propagation (`_load_records_write`), and
`_create_all_specific_views` then matches the re-keyed copy — no
duplicate is created.

Customized copies (arch differing from their generic at marking time)
are re-keyed like the others but skipped by the replicate: their custom
arch is preserved but may be outdated. After the upgrade, list them
(specific copies whose `arch_db` differs from their generic's) and
decide by hand: port the customization into the receiver's data, or
drop it.

Fallback when the clean flow cannot run (e.g. the move already shipped
in a released migration): archive the stale copies (`active = False`)
in a `pre-migration` — they are excluded from every inheritance tree,
and the update creates a fresh specific copy carrying the new arch. The
remaining generic + specific pair is the standard COW shape; future
updates propagate to the copy by key.

End state: one generic view under the receiving module and exactly one
specific copy per website, all on the new key, nothing left on the old
key. Render the affected pages in every active language (see Verifying).

### Gotchas that bite while moving views

- `ir_ui_view.key` is a plain stored field: raw-SQL xmlid renames do not
  recompute it, and the stale value drives both the load-time COW
  propagation and `_create_all_specific_views`.
- Update-time validation (`_check_xml` → `_get_combined_arch`) builds
  combined archs WITHOUT the views of modules not loaded yet
  (`_filter_loaded_views`): a positional xpath valid only after a
  sibling view from a later-loading module applied crashes the
  update itself. Prefer structural xpaths.

## Verifying an upgrade that moves records

Upgrade a copy of the production database, never production itself.
Trigger the upgrade with every version-bumped module listed in `-u`
(or `--update all`): a bumped dependency is not upgraded implicitly,
and its migration silently never runs. Then assert:

- One record per moved xmlid, under its new module, with the same
  `res_id` and the **original `create_date`**: a recent date means the
  record was re-created — the re-attribution failed.
- No stale xmlid left under the sending module for the moved records.
- Business data intact: row counts and column values unchanged.
- Full record content of every moved record identical, apart from
  intended changes: compare whole rows (`row_to_json`) including each
  translation language of translatable fields — not just `res_id`
  and `create_date`.
- Whole-table diff of every affected table before/after, to catch
  unintended changes outside the moved records.
- Render the affected pages (portal, website) in EVERY active language
  before and after the upgrade, and diff the HTML (normalize csrf
  tokens and asset bundle hashes): translated archs break
  independently of the English one, and English test databases hide it.
- A second update run is a no-op (idempotent).

Finally, for any module whose data files gained or lost cross-module
references: run a standalone `-i <module>` on a fresh database — undeclared
references crash the data load.
