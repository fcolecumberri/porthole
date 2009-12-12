# -*- coding: utf-8 -*-
#
""" File: porthole/views/hightlight.py
This file is part of the Porthole, a graphical portage-frontend.

Copyright (C) 2006-2009  René 'Necoro' Neumann
This is free software.  You may redistribute copies of it under the terms of
the GNU General Public License version 2.
There is NO WARRANTY, to the extent permitted by law.

Written by  René 'Necoro' Neumann <necoro@necoro.net>
Adapted to Porthole by, Brian Dolbec <dol-sen@users.sourceforge.net>
"""
from __future__ import absolute_import, with_statement

import gtk
#import logging

from porthole.utils import debug
from porthole.views.lazyview import LazyView


class ListView (gtk.TextView, LazyView):

    def __init__ (self, get_file_fn):
        if get_file_fn:
            self.get_fn = get_file_fn
        else:  # assume it is passed a filename already
            self.get_fn = self._get_fn

        gtk.TextView.__init__(self)
        LazyView.__init__(self)

        self.set_editable(False)
        self.set_cursor_visible(False)

    def _get_fn(self, x):
        return x

    def set_text (self, text):
        debug.dprint("LISTVIEW: set_text: " + text[:max(len(text),500)])
        self.get_buffer().set_text(text)

    def _get_content (self):
        try:
            debug.dprint("LISTVIEW: filename to load: " + self.get_fn(self.pkg))
            with open(self.get_fn(self.pkg)) as f:
                return f.readlines()
        except IOError, e:
            return "Error: %s" % e.strerror
