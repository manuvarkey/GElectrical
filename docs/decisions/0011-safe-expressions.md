# 0011. Safe expression evaluation replaces `eval`, Mako and pickle

- Status: Accepted (owner 2026-11-26)
- Date: 2026-11-26
- Related: [audit §12](../migration/existing-application-audit.md#12-defects-and-weaknesses) (D1–D3, D10)

## Context

Protection-curve definitions (stored in databases **and inside project
files**), rules-check expressions, numeric field entry and database references
are evaluated with Python `eval()`. Copy/paste uses pickle through the system
clipboard. Symbol labels use Mako templates. Once files arrive from untrusted
sources or MCP clients edit projects, these paths allow arbitrary code
execution.

## Decision

- Implement `gelectrical/core/expressions.py`, a bounded AST evaluator with an
  explicit whitelist: numeric literals, lists, names from a supplied namespace,
  attribute access on whitelisted wrapper objects (`f`, `d`, `e.f`, `e.r`, `ss`,
  `sr`), arithmetic, comparisons, boolean operators, conditional expressions
  and calls to whitelisted functions. No dunder names, imports, lambdas,
  comprehensions or arbitrary calls. Limits on length, depth and evaluation cost.
- Rules-check expressions (code-defined) use the same evaluator so behaviour is
  uniform.
- Numeric entry uses the numeric subset (inspired by GEstimator's
  `NumericExpression`).
- Database tuple references use `ast.literal_eval` or a migrated column.
- Clipboard uses a versioned JSON payload validated by Python.
- Symbol labels are produced by Python formatting functions, not Mako.

## Alternatives considered

- *`asteval` or `simpleeval` libraries*: possible, but their default feature
  sets are broader than needed and attribute access rules differ; a small local
  evaluator is auditable. Re-evaluate if the local evaluator grows.
- *Keep eval with restricted globals*: not a security boundary.

## Consequences

Some unusual expressions in user projects might be rejected; they are reported
with element and field, never executed or silently replaced.

## Verification

Every bundled expression parses; curve and rules baselines unchanged; malicious
project and clipboard samples are rejected; CI static check forbids `eval`,
`exec` and `pickle.loads` in engine and backend code.
