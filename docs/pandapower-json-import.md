## Inspect an external Pandapower JSON network

Use **Import Pandapower JSON (read-only)...** in the project-opening popover to select a JSON network exported by Pandapower or by GElectrical's analysis export.

GElectrical loads the file with Pandapower and displays a summary of the populated network element tables. This import is intentionally read-only: it does not recreate the original GElectrical schematic, create a native `.gepro` project, or replace the currently open project. Continue using the normal project-opening action for native `.gepro` files.

The preview reports counts for buses, lines, transformers, loads, generators, external grids, switches and other supported standard Pandapower tables. Invalid or empty files are rejected with an error message.

