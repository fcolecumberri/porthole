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

    def __init__(self, prefs, call_back, history = None):
        # setup glade
        self.gladefile = "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "run_dialog")
        # register callbacks
        callbacks = {"on_execute" : self.execute,
                     "on_cancel" : self.cancel}
        self.wtree.signal_autoconnect(callbacks)
        self.command = None
        self.call_back = call_back
        self.history = ["", "emerge ",
                        "ACCEPT_KEYWORDS='~x86' emerge ",
                        "USE=' ' emerge ",
                        "ACCEPT_KEYWORDS='~x86' USE=' ' emerge"]
        self.prefs = prefs
        self.window = self.wtree.get_widget("run_dialog")
        self.combo = self.wtree.get_widget("combo")
        self.entry = self.wtree.get_widget("combo-entry")
        self.list = self.wtree.get_widget("combo-list")
        #self.window.set_title("Porthole")
        self.combo.set_popdown_strings(self.history)
        self.entry.connect("activate", self.activate, self.command)
        if self.prefs:
            self.window.resize(self.prefs.run_dialog.width, 
                                self.prefs.run_dialog.height)
            # MUST! do this command last, or nothing else will _init__
            # after it until emerge is finished.
            # Also causes runaway recursion.
            self.window.connect("size_request", self.on_size_request)

    def activate(self, widget, command):
        self.command = self.entry.get_text()
        if self.command:
            dprint("COMMAND: activated :%s" %self.command)
            self.call_back(("command line entry: %s" %self.command), self.command)
        self.cancel(None)
        
    def execute(self, widget):
        """Adds the command line entry to the queue"""
        self.command = self.entry.get_text()
        if self.command:
            dprint("COMMAND: run_dialog : %s" %self.command)
            self.call_back("command line entry", self.command)
        self.cancel(None)

    def cancel(self, widget):
        """cancels run dialog"""
        self.wtree.get_widget("run_dialog").destroy()
        

    def on_size_request(self, window, gbox):
        """ Store new size in prefs """
        # get the width and height of the window
        width, height = window.get_size()
        # set the preferences
        self.prefs.run_dialog.width = width
        self.prefs.run_dialog.height = height


