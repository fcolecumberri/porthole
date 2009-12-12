# -*- coding: utf-8 -*-
#
""" File: porthole/views/lazyview.py
This file is part of the Porthole, a graphical portage-frontend.

Copyright (C) 2006-2009 René 'Necoro' Neumann
This is free software.  You may redistribute copies of it under the terms of
the GNU General Public License version 2.
There is NO WARRANTY, to the extent permitted by law.

Written by  René 'Necoro' Neumann <necoro@necoro.net>
Adapted to Porthole by, Brian Dolbec <dol-sen@users.sourceforge.net>
"""
#from __future__ import absolute_import, with_statement

#import logging

from porthole.utils import debug

class LazyView (object):
    def __init__ (self):
        #self.connect("map", self.cb_mapped)

        self.pkg = None
        self.updated = False

    def update (self, pkg, force = False):
        #debug.dprint("LazyView:, update(), pkg = " + pkg)
        self.pkg = pkg
        self.ebuild = None
        self.updated = True
        
        if force:
            self.cb_mapped()


    def cb_mapped (self, *args):
        if self.updated and self.pkg:
            self.set_text("".join(self._get_content()))
            self.updated = False
        return False

    def set_text (self, text):
        raise NotImplementedError

    def _get_content (self):
        raise NotImplementedError

