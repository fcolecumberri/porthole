#!/usr/bin/env python

'''
    Porthole Utils Package
    Holds common functions for Porthole

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

import pygtk
pygtk.require("2.0") #make sure we have the right version
import gtk, portagelib
import os, grp
from sys import stderr

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
    #if it's installed, find out if it can be upgraded
    if package.is_installed:
        installed = package.get_installed()
        installed.sort()
        latest_installed = portagelib.get_version(installed[-1])
        latest_available = portagelib.get_version(package.get_latest_ebuild(0))
        if latest_installed == latest_available:
            #they are the same version, so you are up to date
            icon = gtk.STOCK_YES
        else:
            if latest_installed > latest_available:
                #it's a downgrade!
                icon = gtk.STOCK_GO_BACK
            else:
                #let the user know there is an upgrade available
                icon = gtk.STOCK_GO_FORWARD
    else:
        #just put the STOCK_NO icon
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

