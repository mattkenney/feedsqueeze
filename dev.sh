#!/bin/sh

APPDIR=$( cd "$( dirname "$0" )" && pwd )
SCRIPTNAME=$( basename "$0" )
GAE_HOME=/usr/local/google_appengine
PYTHON=python2.5

# online YUI compressor via http://refresh-sf.com/yui/
do_compress()
{
    for src in static_src/css/*.css
    do
        if [ -f "$src" ] && [ -r "$src" ]
        then
            base=$( basename "$src" )
            dst=static/css/$base
            if [ ! -e "$dst" ] || [ "$src" -nt "$dst" ]
            then
                echo "compressing css $src"
                curl -L -F "compressfile[]=@$src;filename=$base" -F type=CSS -F redirect=on http://refresh-sf.com/yui/ > "$dst"
                if grep -q [ERROR] "$dst"
                then
                    echo $( cat "$dst" )
                fi
            fi
        fi
    done
    for src in static_src/js/*.js
    do
        if [ -f "$src" ] && [ -r "$src" ]
        then
            base=$( basename "$src" )
            dst=static/js/$base
            if [ ! -e "$dst" ] || [ "$src" -nt "$dst" ]
            then
                echo "compressing js $src"
                curl -L -F "compressfile[]=@$src;filename=$base" -F type=JS -F semi=on -F redirect=on http://refresh-sf.com/yui/ > "$dst"
                if grep -q [ERROR] "$dst"
                then
                    echo $( cat "$dst" )
                fi
            fi
        fi
    done
}

case "$1" in
    clean)
        find "$APPDIR" -name '*~' -delete
        find "$APPDIR" -name '*.pyc' -delete
        ;;

    compress)
        do_compress
        ;;

    deploy)
        "$PYTHON" "$GAE_HOME/appcfg.py" update "$APPDIR"
        ;;

    run)
        "$PYTHON" "$GAE_HOME/dev_appserver.py" -a 0.0.0.0 "$APPDIR"
        ;;

    *)
        echo "Usage: $SCRIPTNAME {clean|compress|deploy|run}" >&2
        exit 3
        ;;
esac
