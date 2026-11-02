# Testing

How Odoo tests should be organized and written.

## Organization

- Tests live in `tests/`, named `test_<topic>.py` after the model or
  behavior under test (`test_res_partner.py`).
- One class per feature under test; one test method per behavior, named
  `test_<action>__<expected_outcome>`.
- Inherit `BaseCommon` (`from odoo.addons.base.tests.common import
  BaseCommon`) as the default test base — core-provided since 16.0. It
  disables mail/tracking noise by default (`tracking_disable`,
  `mail_create_nolog`, ...) and provides fixtures (`cls.company`,
  `cls.partner`, group refs) and helpers (`_create_company`,
  `_create_new_internal_user`, `quick_ref`, ...). Override
  `default_env_context()` when tracking/mail is the behavior under test;
  use plain `TransactionCase` only when the mail-disabled context or the
  fixtures do not fit.
- `@tagged('at_install')` is the default; use `@tagged('post_install')`
  only when the behavior needs the module's *installed* state (data across
  modules, mail templates, ...).
- Tests must not depend on each other's data or on execution order;
  share module-specific fixtures and helpers in `tests/common.py`, as
  mixin classes combined with the core base class.

## Test data

- Run tests on a fresh database built by module installs, never on a
  restored production dump: dumps carry production-specific state
  (customer configuration, real records) that makes failures misleading.
- Create the data each test needs; never rely on demo data (not installed
  by default from 19.0 on — see `versions/19.0.md`).
- Build the minimal record set that exercises the behavior: heavy setup
  hides what the test is about.
- Mock external services (HTTP, SMTP, ...): tests never reach the
  network.

## What to test

- Business logic: computed values, constraint rejections, state
  transitions, business methods — never Odoo core itself.
- Security: read/write attempts from a limited user (ACL and record rule
  enforcement).
- Regressions: every bug fix ships a test that fails without the fix.
- Assert observable outcomes (field values, raised errors), not
  implementation details.

## Tours (JS)

- A tour test only when the JS behavior itself is under test;
  server-side behavior belongs in normal tests.
- One flow per tour; keep it minimal.
