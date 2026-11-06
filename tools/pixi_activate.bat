@echo off
REM Register the librsvg gdk-pixbuf loader (needed for SVG element icons).
REM conda-forge's prebuilt loaders.cache on Windows omits the svg loader, so
REM regenerate it when missing or when svg is not listed.
set "_GE_PIXBUF_CACHE=%CONDA_PREFIX%\Library\lib\gdk-pixbuf-2.0\2.10.0\loaders.cache"
findstr /m /c:"svg" "%_GE_PIXBUF_CACHE%" >nul 2>&1 || "%CONDA_PREFIX%\Library\bin\gdk-pixbuf-query-loaders.exe" --update-cache
set "_GE_PIXBUF_CACHE="

REM Compile GSettings schemas (GtkFileChooser aborts the app without them).
set "_GE_SCHEMAS=%CONDA_PREFIX%\Library\share\glib-2.0\schemas"
if not exist "%_GE_SCHEMAS%\gschemas.compiled" "%CONDA_PREFIX%\Library\bin\glib-compile-schemas.exe" "%_GE_SCHEMAS%"
set "_GE_SCHEMAS="
