#!/usr/bin/env python

'''
    Porthole command line entry Dialog
    Shows information about Porthole

    Copyright (C) 2003 - 2004 Fredrik Arnerup, Daniel G. Taylor
                                Brian Dolbec and William F. Wheeler

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
from utils import dprint
from version import version

class RunDialog:
    """Class to hold about dialog and functionality."""

    def __init__(self, prefs = None, history = None, command = None):
        # setup glade
        self.gladefile = "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "run_dialog")
        # register callbacks
        callbacks = {"on_execute" : self.execute,
                     "on_cancel" : self.cancel}
        self.wtree.signal_autoconnect(callbacks)
        self.command = command
        self.history = history
        self.prefs = prefs
        self.window = self.wtree.get_widget("run_dialog")
        self.entry = self.wtree.get_widget("combo-entry")
        self.list = self.wtree.get_widget("combo-list")
        #window.set_title("Porthole")
        self.entry.connect("activate", execute, command)

    def execute(self, widget, command):
        """Adds the command line entry to the queue"""
        if command:
            self.command = command
        self.wtree.get_widget("run_dialog").destroy()


    def cancel(self, widget):
        """cancels run dialog"""
        self.wtree.get_widget("about_dialog").destroy()

    def run(self):
        """main dialog control"""
        # start the entry off with something usefull
        self.entry.set_text("emerge ")
        self.list.set_popdown_strings(self.history)




