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

import gi; gi.require_version("Gtk", "3.0") # make sure we have the right version
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk

#from gettext import gettext as _

#from porthole.utils import debug
from porthole.views.sorts import (
    size_sort_func,
    latest_sort_func,
    installed_sort_func
)

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
    store = Gtk.TreeStore(
        GObject.TYPE_STRING,        # 0: package name
        GObject.TYPE_BOOLEAN,       # 1: checkbox value in upgrade view
        GObject.TYPE_PYOBJECT,      # 2: package object
        GdkPixbuf.Pixbuf,             # 3: room for various icons
        GObject.TYPE_BOOLEAN,       # 4: true if package is in 'world' file
        GObject.TYPE_STRING,        # 5: foreground text colour
        GObject.TYPE_STRING,        # 6: size
        GObject.TYPE_STRING,        # 7: installed version
        GObject.TYPE_STRING,        # 8: portage recommended version
        GObject.TYPE_STRING,        # 9: description
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
    model = Gtk.TreeStore(GObject.TYPE_STRING,  # 0 partial category name
                          GObject.TYPE_STRING,  # 1 full category name
                          GObject.TYPE_STRING)  # 2 pkg count, use string so it can be blank
    return model


