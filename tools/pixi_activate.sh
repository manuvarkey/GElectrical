# Register the librsvg gdk-pixbuf loader (needed for SVG element icons).
cache="$CONDA_PREFIX/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"
if [ ! -f "$cache" ] || ! grep -q svg "$cache"; then
    gdk-pixbuf-query-loaders --update-cache
fi
