#!/usr/bin/env python

'''
    Porthole Depends TreeModel
    Calculates and stores package dependency information

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
import gtk, gobject, portagelib, string
from utils import get_icon_for_package

class DependsTree(gtk.TreeStore):
    """Calculate and display dependencies in a treeview"""
    def __init__(self):
        """Initialize the TreeStore object"""
        gtk.TreeStore.__init__(self, gobject.TYPE_STRING,
                                gtk.gdk.Pixbuf,
                                gobject.TYPE_PYOBJECT)
        
    def parse_depends_list(self, depends_list, parent = None):
        """read through the depends list and order it nicely"""
        new_list = []
        for depend in depends_list:
            if depend[len(depend) - 1] == "?":
                if depend[0] != "!":
                    parent = "Using " + depend[:len(depend) - 1]
                else:
                    parent = "Not Using " + depend[1:len(depend) - 1]
            else:
                if depend != "(" and depend != ")":
                    new_list.append((parent, depend))
        return new_list
                    

    def add_depends_to_tree(self, depends_list, depends_view, parent = None):
        """Add all dependencies to the tree"""
        depends_list = self.parse_depends_list(depends_list)
        parent_iter = parent
        last_flag = None
        for use_flag, depend in depends_list:
            if last_flag != use_flag:
                parent_iter = self.insert_before(parent, None)
                self.set_value(parent_iter, 0, use_flag)
                last_flag = use_flag
            depend_iter = self.insert_before(parent_iter, None)
            self.set_value(depend_iter, 0, depend)
            icon = get_icon_for_package(portagelib.Package(depend))
            self.set_value(depend_iter, 1, 
                                    depends_view.render_icon( icon,
                                    size = gtk.ICON_SIZE_MENU,
                                    detail = None))
            if icon != gtk.STOCK_YES:
                if depend not in self.depends_list:
                    self.depends_list.append(depend)
                    pack = portagelib.Package(depend)
                    ebuild = pack.get_latest_ebuild()
                    depends = string.split(portagelib.get_property(ebuild, "DEPEND"))
                    if depends:
                        self.add_depends_to_tree(depends, depends_view, depend_iter)

    def fill_depends_tree(self, treeview, package):
        """Fill the dependencies tree for a given ebuild"""
        ebuild = package.get_latest_ebuild()
        depends = string.split(portagelib.get_property(ebuild, "DEPEND"))
        self.clear()
        if depends:
            self.depends_list = []
            self.add_depends_to_tree(depends, treeview)
        else:
            parent_iter = self.insert_before(None, None)
            self.set_value(parent_iter, 0, "None")
        treeview.set_model(self)
