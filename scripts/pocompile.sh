#!/bin/bash
# Helper script to compile all .po files in the i18n directroy into .mo files.
# Requires sys-devel/gettext.
#
# Copyright 2005 - 2010  Tommy Iorns, Brian Dolbec, René 'Necoro' Neumann
#

cd ../porthole/i18n

eme=""
if [[ "$1" == "-emerge" ]]; then
    eme="y"
    shift
fi

if [[ $# > 0 ]]; then
    langs="$@"
else
    # in emerge case do not install anything if nothing is given
    if [[ -z $eme ]]; then
        langs="$(ls *.po | sed 's/\.po//g')"
    else
        langs=""
    fi
fi

for lang in ${langs}; do
    item=${lang}.po

    if [[ -f $item ]]; then
        echo "Creating translation file for ${lang}."

        if [[ -n $eme ]]; then
            mkdir mo -p
            msgfmt ${item} -o mo/${lang}.mo
        else
            mkdir ${lang}/LC_MESSAGES -p
            msgfmt ${item} -o ${lang}/LC_MESSAGES/porthole.mo
        fi
    fi
done

cd ..
