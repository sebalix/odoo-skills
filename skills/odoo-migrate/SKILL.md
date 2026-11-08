---
name: odoo-migrate
description: Knowledge companion for migrating an Odoo module between versions — read the common migration patterns and the target version delta before porting code.
---

## Workflow

1. Load the `odoo-knowledge` skill — it routes to the migration references.
2. Read the migration references from `odoo-knowledge`: the module checks
   (`migrations/common-patterns.md`) and the script and record-move patterns
   (`migration-scripts.md`), then the Old → New delta for the target
   version. If migrating across several versions (e.g. 15.0 → 18.0), read
   every intermediate version file in order.
3. If the target version ships automated conversion scripts (Odoo 20.0+:
   the `odoo/upgrade_code/` directory in the Odoo source tree), run
   `odoo-bin upgrade-code` on the module first — they convert the
   machine-convertible changes.
4. Apply the Old → New tables mechanically to the code. The tables are
   authoritative; do not improvise substitutions that are not listed.
5. Flag anything the tables do not cover for manual analysis and research in
   the target version source — do not guess.
