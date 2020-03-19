#!/bin/sh
# Helper script to compile the i18n/messages.pot file.
# Requires sys-devel/gettext and dev-util/intltool.
#
# Copyright 2005 - 2008  Tommy Iorns, Brian Dolbec
#
cd ..
intltool-extract --type="gettext/glade" porthole/glade/porthole.glade
intltool-extract --type="gettext/glade" porthole/glade/advemerge.glade
intltool-extract --type="gettext/glade" porthole/glade/config.glade
intltool-extract --type="gettext/glade" porthole/glade/about.glade

# translatable strings in .glade files extracted to .h files
xgettext -k_ -kN_ -o porthole/i18n/messages.pot porthole/glade/*.h
xgettext -k_ -kN_ -j -o porthole/i18n/messages.pot $(find -name "*.py")


# all python files and .h files placed in i18n/messages.pot
