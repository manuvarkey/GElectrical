@echo off
REM Register the librsvg gdk-pixbuf loader (needed for SVG element icons).
REM conda-forge does not generate loaders.cache on Windows, so build it once.
if not exist "%CONDA_PREFIX%\Library\lib\gdk-pixbuf-2.0\2.10.0\loaders.cache" (
    "%CONDA_PREFIX%\Library\bin\gdk-pixbuf-query-loaders.exe" --update-cache
)
