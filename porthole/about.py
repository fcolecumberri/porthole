#!/usr/bin/env python

'''
    Porthole About Dialog
    Shows information about Porthole

    Copyright (C) 2003 Fredrik Arnerup and Daniel G. Taylor

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

try:
    import pygtk
    pygtk.require("2.0") #make sure we have the right version
except ImportError:
    sys.exit("Error loading libraries!\nIs pygtk installed?")
try:
    import gtk, gtk.glade
except ImportError:
    sys.exit("Error loading libraries!\nIs GTK+ installed?")
try:
    import webbrowser
except: pass

class AboutDialog:
    """Class to hold about dialog and functionality."""

    def __init__(self):
        #setup glade
        self.gladefile = "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "about_dialog")
        #register callbacks
        callbacks = {"on_ok_clicked" : self.ok_clicked,
                     "on_homepage_clicked" : self.homepage_clicked}
        self.wtree.signal_autoconnect(callbacks)

    def ok_clicked(self, widget):
        """Get rid of the about dialog!"""
        self.wtree.get_widget("about_dialog").destroy()

    def homepage_clicked(self, widget):
        """Open Porthole's Homepage!"""
        try:
            webbrowser.open("http://porthole.sourceforge.net")
        except: pass
