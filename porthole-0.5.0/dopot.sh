#!/bin/sh
# Helper script to compile the i18n/messages.pot file.
# Requires sys-devel/gettext and dev-util/intltool.
intltool-extract --type="gettext/glade" porthole.glade
intltool-extract --type="gettext/glade" advemerge.glade
intltool-extract --type="gettext/glade" config.glade
# translatable strings in .glade files extracted to .h files
xgettext -k_ -kN_ -o i18n/messages.pot *.py *.h
# all python files and .h files placed in i18n/messages.pot
