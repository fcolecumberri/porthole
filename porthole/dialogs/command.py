#!/usr/bin/env python

'''
    Porthole command line entry Dialog
    Shows information about Porthole

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor,
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
from gettext import gettext as _

from porthole.utils import debug
from porthole.loaders.loaders import load_web_page
from porthole.version import version
from porthole import config

class RunDialog:
    """Class to hold run dialog and functionality."""

    def __init__(self, call_back, run_anyway=False):
        # setup glade
        self.gladefile = config.Prefs.DATA_PATH + config.Prefs.use_gladefile
        self.wtree = gtk.glade.XML(self.gladefile, "run_dialog")
        # register callbacks
        callbacks = {"on_help" : self.help,
                     "on_execute" : self.execute,
                     "on_cancel" : self.cancel,
                     "on_comboboxentry1_changed" : self.command_changed
                    }
        self.wtree.signal_autoconnect(callbacks)
        self.command = None
        self.call_back = call_back
        self.run_anyway = run_anyway
        if config.Prefs:
            #debug.dprint("COMMAND: config.Prefs == True")
            self.history = config.Prefs.run_dialog.history
        else:
            debug.dprint("COMMAND: config.Prefs == False")
            self.history = ["", "emerge ",
                            "ACCEPT_KEYWORDS='~x86' emerge ",
                            "USE=' ' emerge ",
                            "ACCEPT_KEYWORDS='~x86' USE=' ' emerge"]
        #debug.dprint("COMMAND: self.history:")
        #debug.dprint(self.history)
        self.window = self.wtree.get_widget("run_dialog")
        self.combo = self.wtree.get_widget("comboboxentry1")
        self.entry = self.combo.child
        #self.list = self.wtree.get_widget("combo-list")
        # Build a formatted combo list from the versioninfo list 
        self.comboList = gtk.ListStore(str)
        index = 0
        for x in self.history:
            # Set the combo list
            self.comboList.append([x])
        
        # Set the comboboxentry to the new model
        self.combo.set_model(self.comboList)
        self.combo.set_text_column(0)
        self.entry.connect("activate", self.activate, self.command)
        if config.Prefs:
            self.window.resize(config.Prefs.run_dialog.width, 
                                config.Prefs.run_dialog.height)
            # MUST! do this command last, or nothing else will _init__
            # after it until emerge is finished.
            # Also causes runaway recursion.
            self.window.connect("size_request", self.on_size_request)

    def activate(self, widget, command):
        """Adds the command line entry to the queue"""
        self.command = self.entry.get_text()
        if self.command:
            #debug.dprint("COMMAND: activated: %s" %self.command)
            self.call_back(_("command line entry"), self.command, self.run_anyway)
            self.history_add()
        self.cancel(None)
        
    def execute(self, widget):
        """Adds the command line entry to the queue"""
        self.command = self.entry.get_text()
        if self.command:
            #debug.dprint("COMMAND: execute: %s" %self.command)
            self.call_back(_("command line entry"), self.command, self.run_anyway)
            self.history_add()
        self.cancel(None)

    def cancel(self, widget):
        """cancels run dialog"""
        self.window.destroy()
        
    def help(self, widget):
        """ Display help file with web browser """
        load_web_page('file://' + config.Prefs.DATA_PATH + 'help/custcmd.html', config.Prefs)


    def on_size_request(self, window, gbox):
        """ Store new size in prefs """
        # get the width and height of the window
        width, height = window.get_size()
        # set the preferences
        config.Prefs.run_dialog.width = width
        config.Prefs.run_dialog.height = height

    def history_add(self):
        """adds the command to the history if not already in"""
        if self.command not in self.history:
            length = len(self.history)
            if length > config.Prefs.run_dialog.default_history:
                length = min(length, config.Prefs.run_dialog.history_length)
                old_history = self.history[config.Prefs.run_dialog.default_history:length]
                self.history = self.history[:config.Prefs.run_dialog.default_history]
                self.history.append(self.command)
                self.history += old_history
            else:
                self.history.append(self.command)
            debug.dprint("COMMAND.history_add(): new self.history:")
            debug.dprint(self.history)
        config.Prefs.run_dialog.history = self.history
        return

    def command_changed(self,widget):
        """Updates the gtk.Entry with the history item selected"""
        debug.dprint("COMMAND: changing entry item")
        return # not needed at this time
        model = widget.get_model()
        iter = widget.get_active_iter()
        selection = model.get_value(iter, 0)
        
