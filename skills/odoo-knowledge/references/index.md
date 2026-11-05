# Odoo Best Practices — Knowledge Base Index

Single source of truth for Odoo development best practices. Skills reference
these files; they never duplicate the rules.

## Topic files

Read the file matching the task at hand. Stubbed files contain section
outlines and are pending content.

| File | Read when... | Status |
| ---- | ------------ | ------ |
| `module-structure.md` | Creating a module, reviewing layout/manifest/dependencies | done |
| `orm.md` | ORM: environment, translations, sudo, transactions, overrides (house rules only) | done |
| `security.md` | Sweep rules: sudo, public methods, related fields, raw SQL, domain injection, secrets | done |
| `data.md` | Data files: noupdate records, hooks, per-company records (house rules only) | done |
| `testing.md` | Writing or reviewing tests (organization and content; running them is project-level) | done |
| `comments.md` | Writing or reviewing comments and docstrings (usefulness only) | done |

## Version knowledge

| File | Read when... |
| ---- | ------------ |
| `migrations/common-patterns.md` | Migrating to any version |
| `versions/<X>.md` | Targeting version X, or reviewing code against version X rules |

## Conventions used in this knowledge base

- Rules are imperative and short, with a one-line rationale when not obvious.
- Version-specific rules live only in `versions/`; topic files stay
  version-agnostic.
- Anything a linter/pre-commit can enforce is not documented: run the tools
  instead of re-deriving their findings.
