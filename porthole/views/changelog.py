# -*- coding: utf-8 -*-
#
""" File: porthole/views/changelog.py
This file is part of the Porthole, a graphical portage-frontend.

Copyright (C) 2006-2009 René 'Necoro' Neumann
This is free software.  You may redistribute copies of it under the terms of
the GNU General Public License version 2.
There is NO WARRANTY, to the extent permitted by law.

Written by René 'Necoro' Neumann <necoro@necoro.net>
Adapted to Porthole by, Brian Dolbec <dol-sen@users.sourceforge.net>
"""
#from __future__ import absolute_import, with_statement

import os.path
#import gtk
#import logging

from porthole.utils import debug
from porthole.views.list import ListView
from porthole import backends
portage_lib = backends.portage_lib

class ChangeLogView (ListView):

    def __init__ (self):

        ListView.__init__(self, self._get_fn)

        self.set_editable(False)
        self.set_cursor_visible(False)

    def _get_fn(self, cpv):
        """Returns a path to the specified category/package-version ChangeLog"""
        dir, file = os.path.split(portage_lib.get_path(cpv))
        if dir:
            return os.path.join(dir, "ChangeLog")
        return ''

    def set_text (self, text):
        #debug.dprint(": set_text: " + text[:max(len(text),500)])
        self.get_buffer().set_text(text)

    def _get_content (self):
        try:
            debug.dprint("LISTVIEW: filename to load: " + self.get_fn(self.pkg))
            with open(self.get_fn(self.pkg)) as f:
                return f.readlines()
        except IOError, e:
            return "Error: %s" % e.strerror
