# ORM

House rules for environment, sudo, domains, `Command`, and transaction
handling. Everything else about the ORM (decorators, computed fields,
constraints) follows standard Odoo practice: check modern core modules and
`versions/` when unsure.

## Environment

- Always access through `self.env` (`self.env.cr`, `self.env.uid`,
  `self.env.context`); the legacy attributes (`self._cr`, `self._uid`,
  `self._context`) are removed — see `versions/`.
- Never mutate a context or environment in place: build a new one with
  `with_context()` / `with_user()` / `sudo()` and use that recordset.

## Command

- Write relational fields with the `Command` named constants
  (`from odoo import Command`, available since 15.0):
  `Command.set`, `Command.clear`, `Command.link`, `Command.unlink`,
  `Command.create` — never raw `(6, 0, [...])` tuples in new or
  migrated code.

## Domains

- When a domain filters a relation by company and shared (company-less)
  records are valid, keep them reachable with the compact form
  `[('company_id', 'in', [company_id, False])]`. Do not drop the `False`
  (shared records disappear from the selection), and do not spell out
  the equivalent `['|', ('company_id', '=', False), ('company_id', '=',
  company_id)]`.

## Query object

Since 17.0, `_search()` returns a lazy `Query` object (defined in
`odoo/tools/query.py`, moved to `odoo/orm/query.py` in 20.0) instead of a
list of ids. Nothing hits the database until the query is needed.

- Get one: `query = self._search(domain)` (access-checked), or
  `records._as_query()` to build one from an existing recordset.
- Inject it in a domain instead of fetching ids in Python:
  `[('id', 'in', query)]` — the ORM generates a SQL sub-select (and injects
  the memoized ids when already known).
- Turn it back into a recordset with `self._fetch_query(query, field_names)`
  (fields prefetched; this is what `search_fetch` uses internally).
- Tweak before execution: `query.limit`, `query.offset`,
  `query.order = ...`; check cheaply with `query.is_empty()`.
- In `_search` overrides, modify and return the `Query` — do not force it
  into a list of ids and search again.

## sudo

- `sudo()` only where privileged access is genuinely required, and as
  narrow as possible: latest possible call, smallest recordset.
- Never return a sudo-ed recordset to the web layer (actions, views,
  controllers).
- Prefer `with_user(...)` when the need is a specific user rather than
  bypassed rights.
- Security implications of `sudo` misuse: see `security.md`.

## Transactions

- `cr.commit()` is forbidden in business code: it breaks rollback-on-error
  and partial module upgrades. Justified only in standalone scripts with
  explicit, documented batching.
- Flush pending ORM writes (`flush()`) before raw SQL that reads or
  writes tables the ORM may have modified in-flight.
- Use `with self.env.cr.savepoint():` for error-tolerant partial work
  inside a larger transaction.

## Overrides

- Every override calls `super()` and returns its result.
- Exception: never rewrite the body of an override that predates the
  current change just to add `super()`; leave it and mark it
  `# Full override (no super())`.
- Overrides do not repeat the docstring of the overridden method: the
  base owns the documentation — override-specific, non-obvious notes
  go in comments.
- A field re-declared only to tweak attributes (`groups=""`, `readonly`,
  ...) carries a comment starting "Override to ..." stating what is
  changed and why — the bare declaration is meaningless without its
  intent.
