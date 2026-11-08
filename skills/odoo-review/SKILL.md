---
name: odoo-review
description: Review Odoo module code, diffs, or pull requests for correctness, security, performance, and conventions. Use when asked to review Odoo code, or when a change touches Odoo models, views, security files, or manifests. For OCA migration/port PRs, prefer the odoo-review-oca-migration skill instead.
---

## Workflow

1. Load the `odoo-knowledge` skill — its routing table maps task areas to
   reference files. Read the references matching the areas touched by the
   diff; read only what is relevant to it.
2. Determine the target Odoo version from the module (`__manifest__.py`
   version, branch name, or the `odoo/odoo` git remote). It decides which
   version rules apply; read the odoo-knowledge version reference for it.
3. Check each file in the diff against the applicable rules. Skip style
   issues a linter would catch (pre-commit, flake8, eslint) — focus on what
   tools cannot check. The rules are correctness/best-practice rules, not
   project-specific conventions: they apply to any code under review,
   including community PRs and client projects.
4. Classify every finding:
   - **Blocker**: security hole, data corruption risk, crash, broken behavior.
   - **Should-fix**: convention violation, maintainability or performance issue.
   - **Nit**: minor style or preference; optional to address.
5. Report each finding with `file:line`, the rule violated, and a suggested
   fix. End with a verdict: approve / approve with comments / request changes.

## Quick checklist

- Manifest: version consistent, dependencies declared, license set.
- Models: `@api.depends` complete, decorator order correct,
  computed/inverse pairs coherent.
- Security: `ir.model.access.csv` complete, `ir.rule` where multi-company or
  record isolation applies, no unparameterized SQL, `sudo()` justified.
- Views: inheritance via xpath, unique view ids, `groups` set where required.
- User-facing strings translatable; list values passed to `env._()` unjoined.
- New behavior covered by tests.
- Layering: resources placed with the model they are bound to (mail
  template on `stock.picking` → stock module); no mention of
  non-dependency modules in code; hook docstrings document the contract
  and default, never the overriding module.
- Overrides call `super()` and return its result, or are pre-existing
  bodies marked `# Full override (no super())`; overrides do not
  repeat the base docstring.
- Comments: judge only the ones the change newly adds — comments moved
  with the code stay as they are; useless = restates adjacent code,
  method names, or the docstring.
- Diffs that move records between modules: XML ids re-attributed from
  the receiving module before its data load; migration folder version
  strictly above any version already released (see odoo-knowledge
  `migrations/common-patterns.md`).
