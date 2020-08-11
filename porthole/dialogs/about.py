#!/usr/bin/env python

'''
    Porthole About Dialog
    Shows information about Porthole

    Copyright (C) 2003 - 2020 Fredrik Arnerup and Daniel G. Taylor

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

from porthole.loaders.loaders import (
    get_textfile
)
from porthole.version import (
    copyright,
    version
)
from porthole import config
from porthole import backends

class AboutDialog:
    """Class to hold about dialog and functionality."""

    def __init__(self):
        # setup glade
        self.gladefile = config.Prefs.DATA_PATH + 'glade/about.glade' #config.Prefs.use_gladefile
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)
        self.builder.set_translation_domain(config.Prefs.APP)
        self.window = self.builder.get_object("about")
        license_file = backends.portage_lib.settings.portdir + "/licenses/GPL-2"
        author_file = config.Prefs.AUTHORS
        translator_file = config.Prefs.TRANSLATORS
        self.window.set_property("authors", get_textfile(author_file).split('\n'))
        self.window.set_property("translator_credits", get_textfile(translator_file))
        self.window.set_property("version", version)
        self.window.set_copyright(copyright)
        self.window.set_license(get_textfile(license_file))
        self.window.connect("response", self.close)
        self.open()

    def open(self, *args):
        self.builder.get_object('about').show()

    def close(self, *args):
        return self.builder.get_object('about').close()
