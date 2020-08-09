#!/usr/bin/env python

'''
    Porthole About Dialog
    Shows information about Porthole

    Copyright (C) 2003 - 2008 Fredrik Arnerup and Daniel G. Taylor

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

from gi.repository import Gtk

from gettext import gettext as _

from porthole.utils import debug
from porthole.loaders.loaders import (
    load_web_page,
    decode_text,
    get_textfile
)
from porthole.version import (
    copyright,
    version
)
from porthole import config
from porthole import backends
portage_lib = backends.portage_lib

class AboutDialog:
    """Class to hold about dialog and functionality."""

    def __init__(self):
        # setup glade
        self.gladefile = config.Prefs.DATA_PATH + 'glade/about.glade' #config.Prefs.use_gladefile
        self.wtree = Gtk.Builder()
        self.wtree.add_from_file(self.gladefile)
        self.wtree.set_translation_domain(config.Prefs.APP)
        self.window = self.wtree.get_object("about")
        self.window.show_all()
        debug.dprint("ABOUT: Showing About dialog")

    def ok_clicked(self, widget):
        """Get rid of the about dialog!"""
        self.wtree.get_object("about_dialog").destroy()

    def homepage_clicked(self, widget):
        """Open Porthole's Homepage!"""
        load_web_page("http://porthole.sourceforge.net")
