# 0010. pixi environment and PyInstaller onedir sidecar

- Status: Accepted (owner 2026-11-26); measurements recorded in M5
- Date: 2026-11-26
- Related: [packaging](../architecture/packaging.md)

## Context

The dev environment is pixi on conda-forge, which provides prebuilt GTK,
pandapower, WeasyPrint natives and the scientific stack on all platforms.
GEstimator uses a pip virtual environment and a PyInstaller `--onefile`
sidecar, which suits its small dependency set.

## Decision

- Keep pixi as the reproducible development and build environment. Add
  features/environments for tests and builds; the GTK dependencies move to a
  `legacy` feature after M2.
- Build the sidecar from the pixi environment with PyInstaller in `--onedir`
  mode, shipped as Tauri resources. Use a packed conda environment as the
  fallback if onedir needs extensive hooks. Do not use `--onefile` (per-start
  extraction of the scientific stack).

## Alternatives considered

- *pip venv + PyInstaller onefile (GEstimator)*: MinGW/Windows build issues for
  some dependencies (documented in AGENTS.md) and slow starts.
- *Embedded python-build-standalone + pip wheels*: viable, but WeasyPrint's
  native libraries are harder to supply than from conda-forge.

## Consequences

Python version and pandapower source are set by
[ADR 0015](0015-python-and-pandapower-versions.md); WeasyPrint on Windows by
[ADR 0016](0016-weasyprint-windows-executable.md).

Release CI installs pixi on each OS runner. Tauri `externalBin` is replaced by
a resource directory and a launcher path in Rust.

## Verification

M5 measurement table: installer and unpacked size, cold/warm start, first
analysis, packaged report export, orphan-process behaviour on Windows and Linux.
