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
from utils import dprint

class DependsTree(gtk.TreeStore):
    """Calculate and display dependencies in a treeview"""
    def __init__(self):
        """Initialize the TreeStore object"""
        gtk.TreeStore.__init__(self, gobject.TYPE_STRING,
                                gtk.gdk.Pixbuf,
                                gobject.TYPE_PYOBJECT)
        self.use_flags = string.split(portagelib.get_portage_environ("USE"))
        
    def parse_depends_list(self, depends_list, parent = None):
        """Read through the depends list and order it nicely
           Returns a list of (parent, dep, satisfied) for each dep"""
        new_list = []
        for depend in depends_list:
            if depend[len(depend) - 1] == "?":
                if depend[0] != "!":
                    parent = "Using " + depend[:len(depend) - 1]
                else:
                    parent = "Not Using " + depend[1:len(depend) - 1]
            else:
                if depend not in ["(", ")", ":"]:
                    depend, ops = self.get_ops(depend)
                    depend2 = None
                    if ops: #should only be specific if there are operators
                        depend2 = portagelib.extract_package(depend)
                    if not depend2:
                        depend2 = depend
                    latest_installed = portagelib.Package(depend2).get_installed()
                    if latest_installed:
                        if ops:
                            satisfied = self.is_dep_satisfied(latest_installed[0], depend, ops)
                        else:
                            satisfied = True
                    else:
                        satisfied = False
                    #print parent, depend, ops, satisfied
                    new_list.append((parent, depend, satisfied))
        return new_list
                    

    def add_depends_to_tree(self, depends_list, depends_view, parent = None):
        """Add all dependencies to the tree"""
        depends_list = self.parse_depends_list(depends_list)
        parent_iter = parent
        last_flag = None
        for use_flag, depend, satisfied in depends_list:
            if last_flag != use_flag:
                parent_iter = self.insert_before(parent, None)
                self.set_value(parent_iter, 0, use_flag)
                if use_flag[0] == "U":
                    flag = use_flag[6:]
                    icon = flag in self.use_flags and gtk.STOCK_YES or gtk.STOCK_NO
                else:
                    flag = use_flag[9:] 
                    icon = flag in self.use_flags and gtk.STOCK_NO or gtk.STOCK_YES
                self.set_value(parent_iter, 1, depends_view.render_icon(icon,
                                    size = gtk.ICON_SIZE_MENU, detail = None))
                last_flag = use_flag
            depend_iter = self.insert_before(parent_iter, None)
            self.set_value(depend_iter, 0, depend)
            #icon = get_icon_for_package(portagelib.Package(depend))
            if satisfied:
                icon = gtk.STOCK_YES
            else:
                icon = gtk.STOCK_NO
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

    def get_ops(self, depend):
        """No, this isn't IRC...
           Returns depend with the operators cut out, and the operators"""
        op = depend[0]
        if op == ">" or op == "<" or op == "=" or op == "!":
            op2 = depend[1]
            if op2 == "=":
                depend = depend[2:]
                return depend, op + op2
            else:
                depend = depend[1:]
                return depend, op
        else:
            return depend, None

    def is_dep_satisfied(self, installed_ebuild, dep_ebuild, operator = "="):
        """Returns True if (installed_ebuild <operator> dep_ebuild) is True, else False
           Valid operators are "=", ">", "<", ">=", and "<=" """
        retval = False
        ins_ver = portagelib.get_version(installed_ebuild)
        dep_ver = portagelib.get_version(dep_ebuild)
        if operator == "=":
            retval = (ins_ver == dep_ver)
        elif operator == ">":
            retval = (ins_ver > dep_ver)
        elif operator == "<":
            retval = (ins_ver < dep_ver)
        elif operator == ">=":
            retval = (ins_ver >= dep_ver)
        elif operator == "<=":
            retval = (ins_ver <= dep_ver)
        else:
            portagelib.dprint("Invalid operator passed to is_dep_satisfied()!")
        return retval

    def fill_depends_tree(self, treeview, package):
        """Fill the dependencies tree for a given ebuild"""
        dprint("Updating deps tree for " + package.get_name())
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
