# Register the librsvg gdk-pixbuf loader (needed for SVG element icons).
cache="$CONDA_PREFIX/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"
if [ ! -f "$cache" ] || ! grep -q svg "$cache"; then
    gdk-pixbuf-query-loaders --update-cache
fi

# Compile GSettings schemas (GtkFileChooser aborts the app without them).
schemas="$CONDA_PREFIX/share/glib-2.0/schemas"
if [ ! -f "$schemas/gschemas.compiled" ]; then
    glib-compile-schemas "$schemas"
fi
