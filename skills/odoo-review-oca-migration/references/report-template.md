# Report template — OCA migration / port PR review

Produce the report in English, following this structure:

```markdown
# Review: OCA/<repo>#<n> — <title>

## Verdict
<PR type, module, SOURCE→TARGET, overall assessment, blockers if any>

## PR metadata
- author / base / head / draft / CI summary / existing reviews and comments
  (points already raised by maintainers)

## Commit fidelity
| PR commit | subject | original | status | notes |
|-----------|---------|----------|--------|-------|

## Completeness
- missing commits / blacklisted (intentional) / out-of-scope commits

## OCA checklist
- [x] / [ ] items with evidence

## Findings
<!-- Finer scale than odoo-review/odoo-audit (blocker / should-fix / nit):
     Major/Minor split the should-fix tier — deliberate for PR reviews. -->
### Blocker
### Major
### Minor
### Nit
### Positive notes

## Suggested review comment
<paste-ready, concise, factual English comment; cite commits and the
migration guide where relevant; do not claim tests were run beyond what CI
shows>

## Uncertainties
<force-pushes, squashed history, rate limits, ambiguous intent — anything not
fully verifiable>
```
