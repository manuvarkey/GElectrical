# 0008. `.gepro` compatibility policy and stable identifiers

- Status: Accepted (owner 2026-11-26)
- Date: 2026-11-26
- Related: [project format](../architecture/project-format.md), [regression baseline](../migration/regression-baseline.md)

## Context

Projects store elements by list position; assemblies reference children by
`[page, index]`. The loader ignores unknown keys and copies field values only
when key and type match. Services, the frontend and MCP need stable element
identity.

## Decision

1. All existing `.gepro` files remain loadable indefinitely.
2. Additive keys that the legacy loader ignores (`uid` on elements and pages,
   `children_uids` on assemblies, `app` provenance) are written without changing
   `GELECTRICAL_FILE_REFERENCE_VER_0`, as long as legacy loading gives identical
   results (tested while the legacy code exists).
3. Breaking changes require `VER_1`, a migration function, tests and an ADR.
4. Element codes and field codes are permanent; meaning changes require new
   codes plus migration.
5. Saves become atomic with a backup.

## Alternatives considered

- *Bump the version immediately to a new modern format*: forces a one-way
  migration early and breaks the legacy app during the transition.
- *Keep positional identity in services*: fragile across deletes, reorders and
  concurrent MCP/desktop edits.

## Consequences

Files saved by the modern app open in the legacy GTK app during migration.
Positional `children_codes` must be kept consistent with `children_uids` on save.

## Verification

Round-trip tests: legacy → modern → legacy with baseline equality; modern-saved
files in the legacy loader.
