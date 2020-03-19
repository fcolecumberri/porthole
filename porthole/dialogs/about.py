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

import gtk, gtk.glade

from porthole.utils import debug
from porthole.loaders.loaders import load_web_page, decode_text, get_textfile
from porthole.version import version, copyright
from porthole import config
from porthole import backends
portage_lib = backends.portage_lib

class AboutDialog:
    """Class to hold about dialog and functionality."""

    def __init__(self):
        # setup glade
        self.gladefile = config.Prefs.DATA_PATH + 'glade/about.glade' #config.Prefs.use_gladefile
        self.wtree = gtk.glade.XML(self.gladefile, "about_dialog", config.Prefs.APP)
        # register callbacks
        callbacks = {"on_ok_clicked" : self.ok_clicked,
                     "on_homepage_clicked" : self.homepage_clicked}
        self.wtree.signal_autoconnect(callbacks)
        self.wtree.get_widget('porthole-about-img').set_from_file(config.Prefs.DATA_PATH + "pixmaps/porthole-about.png")
        self.copyright = self.wtree.get_widget('copyright_label')
        self.copyright.set_label(copyright)
        self.authorview = self.wtree.get_widget('authorview')
        self.licenseview = self.wtree.get_widget('licenseview')
        license_file = portage_lib.settings.portdir + "/licenses/GPL-2"
        author_file = config.Prefs.AUTHORS
        self.licenseview.get_buffer().set_text(decode_text(get_textfile(license_file)))
        self.authorview.get_buffer().set_text(decode_text(get_textfile(author_file)))
        window = self.wtree.get_widget("about_dialog")
        window.set_title(_("About Porthole %s") % version)
        debug.dprint("ABOUT: Showing About dialog")

    def ok_clicked(self, widget):
        """Get rid of the about dialog!"""
        self.wtree.get_widget("about_dialog").destroy()

    def homepage_clicked(self, widget):
        """Open Porthole's Homepage!"""
        load_web_page("http://porthole.sourceforge.net")
