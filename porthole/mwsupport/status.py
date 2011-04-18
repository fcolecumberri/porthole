#!/usr/bin/env python

'''
    Porthole Mainwindow statusbar support
    Support class and functions for the mainwindow interface

    Copyright (C) 2003 - 2011
    Fredrik Arnerup, Brian Dolbec,
    Daniel G. Taylor, Wm. F. Wheeler, Tommy Iorns

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
'''


from gettext import gettext as _

from porthole import db
from porthole.utils import debug

from porthole.mwsupport.constants import (SHOW_ALL,
    SHOW_INSTALLED, SHOW_SEARCH, SHOW_UPGRADE, SHOW_DEPRECATED, SHOW_SETS)


class StatusHandler(object):
    '''Support functions for maintaining the status/progreess bar'''

    def __init__(self,  statusbar,
                        progressbar,
                        category_view,
                        package_view,
                        current_pkg_path,
                        current_pkg_cursor,
                        plugin_views
                        ):

        self.statusbar2 = statusbar
        self.current_pkg_path = current_pkg_path
        self.current_pkg_cursor = current_pkg_cursor
        self.progressbar = progressbar
        self.plugin_views = plugin_views
        self.package_view = package_view
        self.category_view = category_view
        self.status_root = 'Initiallizing StatusHandler ;)'

    def set_statusbar2(self, to_string):
        """Update the statusbar without having to use push and pop."""
        #debug.dprint("StatusHandler: set_statusbar2(); " + string)
        self.statusbar2.pop(0)
        self.statusbar2.push(0, to_string)

    def progress(self, text='', fraction=0):
        """sets the progressbar's text and/or fraction displayed'"""
        self.progressbar.set_text(text)
        self.progressbar.set_fraction(fraction)

    def progress_done(self):
        """clears the progress bar"""
        self.progressbar.set_text("")
        self.progressbar.set_fraction(0)
        self.status_root = _("Done: ")
        self.set_statusbar2(self.status_root)

    def update_statusbar(self, mode, reader=None):
        """Update the statusbar for the selected filter"""
        text = ""
        if mode in self.plugin_views:
            text = self.plugin_views[mode]()
        elif mode == SHOW_ALL:
            if not db.db:
                debug.dprint("StatusHandler: update_statusbar(); " +
                    "attempted to update with no db assigned")
            else:
                text = (_("%(pack)d packages in %(cat)d categories")
                        % {'pack':len(db.db.list),
                        'cat':len(db.db.categories)})
        elif mode == SHOW_INSTALLED:
            if not db.db:
                debug.dprint("StatusHandler: update_statusbar(); " +
                    "attempted to update with no db assigned")
            else:
                text = (_("%(pack)d packages in %(cat)d categories")
                        % {'pack':db.db.installed_count,
                        'cat':len(db.db.installed)})
        elif mode in [SHOW_SEARCH, SHOW_DEPRECATED, SHOW_SETS]:
            text = ''
        elif mode == SHOW_UPGRADE:
            if not reader:
                debug.dprint("StatusHandler:  update_statusbar(); " +
                    "attempted to update with no reader thread assigned")
            else:
                text = ''
        self.set_statusbar2(self.status_root + text)

