#!/bin/bash
# Helper script to compile all .po files in the i18n directroy into .mo files.
# Requires sys-devel/gettext.
#
# Copyright 2005 - 2008  Tommy Iorns, Brian Dolbec
#

cd ../porthole/i18n
for ITEM in *.po; do
  ITEM2=${ITEM/.po/}
  LANG=${ITEM2/_??/}
  mkdir -p ${LANG}/LC_MESSAGES
  msgfmt ${ITEM} -o ${LANG}/LC_MESSAGES/porthole.mo
done
cd ..
