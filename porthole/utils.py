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

try:
    import webbrowser
    web = True
except ImportError:
    print "Web browser module not found, you will not be able to load links"
    web = False

def load_web_page(name):
    if web:
        webbrowser.open(name)

def get_icon_for_package(package):
    """Return an icon for a package"""
    #if it's installed, find out if it can be upgraded
    if package.is_installed:
        installed = package.get_installed()
        installed.sort()
        latest_installed = installed[-1]
        latest_available = package.get_latest_ebuild()
        if latest_installed == latest_available:
            #they are the same version, so you are up to date
            icon = gtk.STOCK_YES
        else:
            #let the user know there is an upgrade available
            icon = gtk.STOCK_GO_FORWARD
    else:
        #just put the STOCK_NO icon
        icon = gtk.STOCK_NO
    return icon
