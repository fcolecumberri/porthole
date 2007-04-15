#!/usr/bin/env python

'''
    Porthole Views
    The view filter classes

    Copyright (C) 2003 - 2006 Fredrik Arnerup, Daniel G. Taylor, Brian Dolbec,
    Brian Bockelman, Tommy Iorns

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

import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, gobject

#import utils.debug
from helpers import *
from sorts import *

#from gettext import gettext as _


def PackageModel():
    """Common model for a package Treestore"""
    store = gtk.TreeStore(
        gobject.TYPE_STRING,        # 0: package name
        gobject.TYPE_BOOLEAN,       # 1: checkbox value in upgrade view
        gobject.TYPE_PYOBJECT,      # 2: package object
        gtk.gdk.Pixbuf,             # 3: room for various icons
        gobject.TYPE_BOOLEAN,       # 4: true if package is in 'world' file
        gobject.TYPE_STRING,        # 5: foreground text colour
        gobject.TYPE_STRING,        # 6: size
        gobject.TYPE_STRING,        # 7: installed version
        gobject.TYPE_STRING,        # 8: portage recommended version
        gobject.TYPE_STRING,        # 9: description
    )
    store.set_sort_func(6, size_sort_func)
    store.set_sort_func(8, latest_sort_func)
    store.set_sort_func(7, installed_sort_func)
    return store


