# Security

Rules for the security mistakes an agent is likely to make and the
ecosystem's own code does not consistently answer. ACLs, record rules, and
controller auth follow standard Odoo practice: check modern core modules
when unsure.

## How to use this file

When writing code, apply the sections below. When reviewing or auditing,
sweep the code for each pattern in the table and judge every hit against
its section — a hit is not a finding by itself; the section says what
makes it one.

| Sweep for | Judge against |
| --- | --- |
| `sudo(`, `with_user(` | [sudo and the web layer](#sudo-and-the-web-layer) |
| `Command` payloads in a sudo'd write | [sudo and the web layer](#sudo-and-the-web-layer) |
| public (non-`_`) model methods | [public methods are RPC surface](#public-methods-are-rpc-surface) |
| `related=` field definitions | [related fields read with sudo](#related-fields-read-with-sudo) |
| `cr.execute`, `%`/`.format`/f-strings near SQL | [raw SQL](#raw-sql) |
| domains built from request/RPC values | [domains from user input](#domains-from-user-input) |
| `ir.config_parameter`, key/token/password fields | [secrets](#secrets) |

## `sudo` and the web layer

- Never return records fetched with `sudo()` through a controller, action
  or view: record rules are bypassed, and the leak is silent.
- In a web context, search with the current user's env; escalate to
  `sudo()` only for a specific, justified write, then come back to the
  user env for anything returned to the client.
- A sudo write with raw `Command` payloads in vals executes with sudo on
  the comodel: whitelist command lists like any other user input.
- Usage mechanics of `sudo()` live in `orm.md`.

## Public methods are RPC surface

- Any non-`_`-prefixed model method is callable via RPC with
  attacker-chosen arguments — access rules apply to CRUD, not to method
  calls. Prefix methods with `_` by default; drop the prefix only for
  genuine external entry points, and validate inputs there.

## Related fields read with sudo

- `related` fields are sudo-computed by default (`related_sudo=True`):
  a user-writable `Many2one` pointing at arbitrary records plus a related
  field through it reads the target value with elevated rights. Set
  `related_sudo=False` on chains reaching sensitive data.

## Raw SQL

- Parameterize every value (`cr.execute("... %s", (val,))`); never
  interpolate. The trap is sorting/paging: `ORDER BY` and `LIMIT` cannot
  take parameters — whitelist the accepted values (column names,
  direction) before interpolation.

## Domains from user input

- Never concatenate a user-provided domain onto one that gates access:
  an injected `['|', ...]` widens what the caller can reach. Extend
  domains by combination, or validate the user-supplied keys strictly.

## Secrets

Two-tier policy:

- **General secrets** (database-global: database URLs, shared API
  tokens) go in `ir.config_parameter`. It is readable only by
  `base.group_system` and its getters enforce read access — acceptable
  for shared configuration secrets.
  Reading a parameter from user-context code requires `.sudo()`.
- **Company-dependent or process-dependent secrets** (per-company
  credentials, per-backend tokens) go in a field on the record they
  belong to: `groups=` restricted to the administering group, with
  `widget="password"` in views.
