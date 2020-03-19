#!/usr/bin/env python

'''
    Porthole Views
    The view filter classes

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor, Brian Dolbec,
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
#from gettext import gettext as _

#from porthole.utils import debug
from porthole.views.helpers import *
from porthole.views.sorts import *

MODEL_ITEM = {"name": 0,
                        "checkbox": 1,
                        "package": 2,
                        "icon": 3,
                        "world": 4,
                        "text_colour": 5,
                        "size": 6,
                        "installed": 7,
                        "recommended": 8,
                        "description": 9
                        }


def PackageModel():
    """Common model for a package Treestore"""
    store = gtk.TreeStore(
        gobject.TYPE_STRING,        # 0: package name
        gobject.TYPE_BOOLEAN,     # 1: checkbox value in upgrade view
        gobject.TYPE_PYOBJECT,     # 2: package object
        gtk.gdk.Pixbuf,                   # 3: room for various icons
        gobject.TYPE_BOOLEAN,     # 4: true if package is in 'world' file
        gobject.TYPE_STRING,        # 5: foreground text colour
        gobject.TYPE_STRING,        # 6: size
        gobject.TYPE_STRING,        # 7: installed version
        gobject.TYPE_STRING,        # 8: portage recommended version
        gobject.TYPE_STRING,        # 9: description
    )
    store.set_sort_func(MODEL_ITEM["size"], size_sort_func)
    store.set_sort_func(MODEL_ITEM["recommended"], latest_sort_func)
    store.set_sort_func(MODEL_ITEM["installed"], installed_sort_func)
    return store

C_ITEM = {"short_name": 0,
                                    "full_name": 1,
                                    "count": 2
                                    }

def CategoryModel():
        model = gtk.TreeStore(gobject.TYPE_STRING,       # 0 partial category name
                                   gobject.TYPE_STRING,                         # 1 full category name
                                   gobject.TYPE_STRING)                         # 2 pkg count, use string so it can be blank
        return model


