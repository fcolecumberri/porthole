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
from loaders import load_web_page
from version import version
from gettext import gettext as _

class RunDialog:
    """Class to hold run dialog and functionality."""

    def __init__(self, prefs, call_back):
        # setup glade
        self.gladefile = prefs.DATA_PATH + prefs.use_gladefile
        self.wtree = gtk.glade.XML(self.gladefile, "run_dialog")
        # register callbacks
        callbacks = {"on_help" : self.help,
                     "on_execute" : self.execute,
                     "on_cancel" : self.cancel}
        self.wtree.signal_autoconnect(callbacks)
        self.command = None
        self.call_back = call_back
        self.prefs = prefs
        if self.prefs:
            #dprint("COMMAND: self.prefs == True")
            self.history = self.prefs.run_dialog.history
        else:
            dprint("COMMAND: self.prefs == False")
            self.history = ["", "emerge ",
                            "ACCEPT_KEYWORDS='~x86' emerge ",
                            "USE=' ' emerge ",
                            "ACCEPT_KEYWORDS='~x86' USE=' ' emerge"]
        dprint("COMMAND: self.history:")
        dprint(self.history)
        self.window = self.wtree.get_widget("run_dialog")
        self.combo = self.wtree.get_widget("combo")
        self.entry = self.wtree.get_widget("combo-entry")
        self.list = self.wtree.get_widget("combo-list")
        #self.window.set_title("Porthole")
        if len(self.history):
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
        """Adds the command line entry to the queue"""
        self.command = self.entry.get_text()
        if self.command:
            #dprint("COMMAND: activated: %s" %self.command)
            self.call_back(_("command line entry"), self.command)
            self.history_add()
        self.cancel(None)
        
    def execute(self, widget):
        """Adds the command line entry to the queue"""
        self.command = self.entry.get_text()
        if self.command:
            #dprint("COMMAND: execute: %s" %self.command)
            self.call_back(_("command line entry"), self.command)
            self.history_add()
        self.cancel(None)

    def cancel(self, widget):
        """cancels run dialog"""
        self.window.destroy()
        
    def help(self, widget):
        """ Display help file with web browser """
        load_web_page('file://' + self.prefs.DATA_PATH + 'help/custcmd.html')


    def on_size_request(self, window, gbox):
        """ Store new size in prefs """
        # get the width and height of the window
        width, height = window.get_size()
        # set the preferences
        self.prefs.run_dialog.width = width
        self.prefs.run_dialog.height = height

    def history_add(self):
        """adds the command to the history if not already in"""
        if self.command not in self.history:
            length = len(self.history)
            if length > self.prefs.run_dialog.default_history:
                length = min(length, self.prefs.run_dialog.history_length)
                old_history = self.history[self.prefs.run_dialog.default_history:length]
                self.history = self.history[:self.prefs.run_dialog.default_history]
                self.history.append(self.command)
                self.history += old_history
            else:
                self.history.append(self.command)
            dprint("COMMAND.history_add(): new self.history:")
            dprint(self.history)
        self.prefs.run_dialog.history = self.history
        return
        
