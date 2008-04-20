#!/bin/sh
# Helper script to compile the i18n/messages.pot file.
# Requires sys-devel/gettext and dev-util/intltool.
intltool-extract --type="gettext/glade" ../porthole/glade/porthole.glade
intltool-extract --type="gettext/glade" ../porthole/glade/advemerge.glade
intltool-extract --type="gettext/glade" ../porthole/glade/config.glade
intltool-extract --type="gettext/glade" ../porthole/glade/about.glade
# translatable strings in .glade files extracted to .h files
xgettext -k_ -kN_ -o ../porthole/i18n/messages.pot ../porthole/*.py  ../porthole/advancedemerge/*.py ../porthole/_xml/*.py ../porthole/backends/*.py ../porthole/config/*.py \
    ../porthole/db/*.py ../porthole/dialogs/*.py ../porthole/loaders/*.py ../porthole/packagebook/*.py ../porthole/readers/*.py ../porthole/terminal/*.py  \
    ../porthole/utils/*.py ../porthole/views/*.py  ../porthole/glade/*.h
# all python files and .h files placed in i18n/messages.pot
