#!/usr/bin/env python

'''
    Porthole Utils Package
    Holds common functions for Porthole

    Copyright (C) 2003 - 2004 Fredrik Arnerup and Daniel G. Taylor

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

# initially set debug to false
debug = False

from sys import stderr
from version import version

def dprint(message):
    """Print debug message if debug is true."""
    if debug:
        print >>stderr, message

import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, portagelib
import os, grp, pwd, cPickle

try:
    import webbrowser
except ImportError:
    print >>stderr, ('Module "webbrowser" not found. '
                     'You will not be able to open web pages.')

def load_web_page(name):
    """Try to load a web page in the default browser"""
    try:
        webbrowser.open(name)
    except:
        pass

def get_icon_for_package(package):
    """Return an icon for a package"""
    # if it's installed, find out if it can be upgraded
    if package.is_installed:
        icon = gtk.STOCK_YES
    else:
        # just put the STOCK_NO icon
        icon = gtk.STOCK_NO
    return icon       

def is_root():
    """Returns true if process runs as root."""
    return os.geteuid() == 0
    
write_access = is_root

def read_access():
    """Return true if user is root or a member of the portage group."""
    # Note: you don't have to be a member of portage to read the database,
    # but portage caching will not work
    portage = 250  # is portage guaranteed to be 250?
    try: portage = grp.getgrnam("portage")[2]
    except: pass
    return write_access() or (portage in (os.getgroups() + [os.getegid()]))

def get_treeview_selection( treeview, num):
        """Get the value of whatever is selected in a treeview,
        num is the column"""
        model, iter = treeview.get_selection().get_selected()
        selection = None
        if iter:
            selection = model.get_value(iter, num)
        return selection

def get_user_home_dir():
    """Return the path to the current user's home dir"""
    return pwd.getpwuid(os.getuid())[5]

class CommonDialog(gtk.Dialog):
    """ A common gtk Dialog class """
    def __init__(self, title, parent, message, callback, button):
        gtk.Dialog.__init__(self, title, parent, gtk.DIALOG_MODAL or
                            gtk.DIALOG_DESTROY_WITH_PARENT, (button, 0))
        # add message
        text = gtk.Label(message)
        text.set_padding(5, 5)
        text.show()
        self.vbox.pack_start(text)
        # register callback
        if not callback:
            callback = self.__callback
        self.connect("response", callback)
        self.show_all()
    
    def __callback(self, widget, response):
        # If no callback is given, just remove the dialog when clicked
        self.destroy()

class YesNoDialog(CommonDialog):
    """ A simple yes/no dialog class """
    def __init__(self, title, parent = None,
                 message = None, callback = None):
        CommonDialog.__init__(self, title, parent, message,
                                           callback, "_Yes")
        # add "No" button
        self.add_button("_No", 1)
        

class SingleButtonDialog(CommonDialog):
    """ A simple please wait dialog class """
    def __init__(self, title, parent = None, message = None,
                 callback = None, button = None, progressbar = False):
        CommonDialog.__init__(self, title, parent, message,
                                           callback, button)
        if progressbar:
            self.progbar = gtk.ProgressBar()
            self.progbar.set_text("Loading")
            self.progbar.show()
            self.vbox.add(self.progbar)

class EmergeOptions:
    """ Holds common emerge options """
    def __init__(self):
        # let's get some saved values in here!
        self.pretend = False
        self.fetch = False
        self.verbose = False

    def get_string(self):
        """ Return currently set options in a string """
        opt_string = ' '
        if self.pretend:
            opt_string += '--pretend '
        if self.fetch:
            opt_string += '--fetchonly '
        if self.verbose:
            opt_string += '--verbose '
        return opt_string

class WindowPreferences:
    """ Holds preferences for a window """
    def __init__(self, width = 0, height = 0):
        self.width = width      # width
        self.height = height    # height

class PortholePreferences:
    """ Holds all of Porthole's configurable preferences """
    def __init__(self):
        # setup some defaults
        self.main = WindowPreferences(500, 650)
        self.main.hpane = 280
        self.main.vpane = 250
        self.main.search_desc = False
        self.main.show_nag_dialog = True
        self.process = WindowPreferences(400, 600)
        self.process.width_verbose = 900
        self.emerge = EmergeOptions()
        self.version = version

    def load(self):
        """ Load saved preferences """
        # does ~/.porthole exist?
        home = get_user_home_dir()
        if os.access(home + "/.porthole", os.F_OK):
            if os.access(home + "/.porthole/prefs", os.F_OK):
                # unpickle our preferences
                dprint("Loading pickled user preferences...")
                saved = cPickle.load(open(home + "/.porthole/prefs"))
                try:
                    if saved.version == self.version:
                        self.main = saved.main
                        self.process = saved.process
                        self.emerge = saved.emerge
                    else:
                        dprint("Not using old config, version " + str(saved.version))
                except:
                    dprint("Version information not found, assuming version 0.2")
        else:
            # create the dir
            dprint("~/.porthole does not exist, creating...")
            os.mkdir(home + "/.porthole")

    def save(self):
        """ Save preferences """
        # get home directory
        home = pwd.getpwuid(os.getuid())[5]
        # pickle it baby, yeah!
        dprint("Pickling user preferences...")
        cPickle.dump(self, open(home + "/.porthole/prefs", "w"))
    
