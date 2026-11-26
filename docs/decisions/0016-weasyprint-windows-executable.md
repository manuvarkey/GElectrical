# 0016. WeasyPrint executable on Windows, one pinned version everywhere

- Status: Accepted (owner decision 2026-11-26)
- Date: 2026-11-26
- Related: [packaging](../architecture/packaging.md), [risk R6](../migration/risks-and-decisions.md), [ADR 0010](0010-python-environment-and-sidecar.md)

## Context

WeasyPrint loads Pango, HarfBuzz, fontconfig and GLib through cffi at runtime.
Collecting these libraries into a frozen Windows sidecar is the main packaging
risk (R6). WeasyPrint publishes ready-made Windows builds with each release
(v70.0: `weasyprint-windows-onedir.zip` and `weasyprint-windows-onefile.zip`,
about 32 MB). conda-forge currently has WeasyPrint 69.0; PyPI has 70.0.

## Decision

- **Windows packaged builds** call the official `weasyprint-windows-onedir`
  executable (onedir avoids per-run extraction), shipped as a Tauri resource.
  The Python sidecar does not bundle WeasyPrint or its native libraries on Windows.
- **Development environments (all OSes), Linux, Flatpak and macOS** use the
  WeasyPrint Python package.
- **One version everywhere:** the executable release and the Python package
  are pinned to the same WeasyPrint version. If conda-forge lags, the Python
  package comes from PyPI through pixi `[pypi-dependencies]` (its native
  libraries still come from conda-forge).
- `gelectrical/reports/pdf.py` (proposed) is the single adapter: it renders the
  report HTML and assets into a temporary folder and either calls the Python
  API or runs the executable (`weasyprint <input.html> <output.pdf>` with
  `--base-url` set to that folder), with a timeout and captured stderr.

## Alternatives considered

- *Bundle WeasyPrint and its DLLs in the frozen sidecar*: more PyInstaller hook
  work and a fragile collection of GTK-stack DLLs.
- *Use the executable on every platform*: no official Linux/macOS executable.
- *Different versions per platform*: reports could differ between platforms.

## Consequences

- The report path on Windows depends on an external process: errors must be
  reported clearly, and the executable path is resolved from Tauri resources.
- Defect D10 mitigation on Windows cannot use a Python `url_fetcher`; it relies
  on autoescaped HTML, a temporary folder containing only bundled assets and the
  executable's command-line options (to be reviewed in M5).
- The executable's licence notices (WeasyPrint BSD-3-Clause plus bundled
  LGPL libraries) ship with the installer.

## Verification

M5/M14: packaged Windows report export on a clean machine; report text and
visual parity between Windows (executable) and Linux (Python package) for the
sample projects; version check in CI that the executable and Python package
versions match.
