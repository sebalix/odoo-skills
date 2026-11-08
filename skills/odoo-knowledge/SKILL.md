---
name: odoo-knowledge
description: Knowledge base of rules and conventions for Odoo development — module structure, models and ORM, security, data files, testing, and version-specific deltas. Use for ANY task that touches Odoo code, before writing, changing, or reviewing it: models, fields, views, manifests, security files, data files, tests, or version migrations. Complements the task skills odoo-review, odoo-audit, and odoo-migrate.
---

# Odoo knowledge base

The reference files are authoritative. Before writing, changing, or reviewing
Odoo code, read the file matching each area you touch — do not improvise
conventions.

| Area you touch | Read |
| -------------- | ---- |
| Module layout, manifests, dependencies | `references/module-structure.md` |
| Models, fields, computed methods, ORM, translations | `references/orm.md` |
| XML/QWeb views (forms, lists, templates, inheritance) | `references/views.md` |
| Access rights, record rules, raw SQL | `references/security.md` |
| XML data files, noupdate, demo data | `references/data.md` |
| Migration scripts (`migrations/`), moving records between modules | `references/migration-scripts.md` |
| Tests | `references/testing.md` |

When unsure which area a task touches, read `references/index.md` first — it
maps the topic files.

Version-specific guidance:

1. Determine the target Odoo version first (manifest `version`, branch name,
   or the `odoo/odoo` git remote) — it decides which rules apply.
2. For version-specific work, read `references/versions/<version>.md`.
3. For migrations between versions, read
   `references/migrations/common-patterns.md`,
   `references/migration-scripts.md`, plus every intermediate
   `versions/*.md` between source and target.
