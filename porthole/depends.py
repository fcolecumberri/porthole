#!/usr/bin/env python

'''
    Porthole Depends TreeModel
    Calculates and stores package dependency information

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

import gtk, gobject, portagelib, string
from utils import dprint
from gettext import gettext as _

class DependsTree(gtk.TreeStore):
    """Calculate and display dependencies in a treeview"""
    def __init__(self):
        """Initialize the TreeStore object"""
        gtk.TreeStore.__init__(self, gobject.TYPE_STRING,
                                gtk.gdk.Pixbuf,
                                gobject.TYPE_PYOBJECT,
                                gobject.TYPE_BOOLEAN)
        self.use_flags = portagelib.get_portage_environ("USE").split()
        
    def parse_depends_list(self, depends_list, parent = None):
        """Read through the depends list and order it nicely
           Returns a list of (parent, dep, satisfied) for each dep"""
        new_list = []
        use_list = []
        ops = ""
        using_list=False
        for dep in depends_list:
            #dprint(dep)
            if dep[-1] == "?":
                if dep[0] != "!":
                    parent = _("Using ") + dep[:-1]
                    using_list=True
                else:
                    parent = _("Not Using ") + dep[1:-1]
            else:
                if dep not in ["(", ")", ":", "||"]:
                    satisfied = portagelib.get_installed(dep)
                    if using_list:
                        if [parent,dep,satisfied] not in use_list:
                            use_list.append([parent, dep, satisfied])
                    else:
                        if [parent,dep,satisfied] not in new_list:
                            new_list.append([parent, dep, satisfied])
                if dep == ")":
                    using_list = False
                    parent = None
        return new_list + use_list
                    

    def add_depends_to_tree(self, depends_list, depends_view, base = None):
        """Add dependencies to the tree"""
        #dprint("DEPENDS: Parsing depends list")
        depends_list = self.parse_depends_list(depends_list)
        #dprint("DEPENDS: Finished parsing depends list")
        base_iter = base
        last_parent = None
        for parent, depend, satisfied in depends_list:
            if parent != None and parent != last_parent:
                if parent.startswith(_("Using ")):
                    flag = parent[len(_("Using ")):]
                    parent_icon = flag in self.use_flags and gtk.STOCK_YES or ''
                elif parent.startswith(_("Not Using ")):
                    flag = parent[len(_("Not Using ")):] 
                    parent_icon = flag in self.use_flags and '' or gtk.STOCK_YES
                else:
                    dprint("Freak out!: What's going on?")
                if base == None:
                    base_iter = self.insert_before(base, None)
                    self.set_value(base_iter, 0, parent)
                    self.set_value(base_iter, 1, depends_view.render_icon(parent_icon,
                                        size = gtk.ICON_SIZE_MENU, detail = None))
                    dep_before = base_iter
                last_parent = parent
            elif parent == None:
                dep_before = base
            else:
                dep_before = base_iter
            #self.set_value(depend_iter, 0, depend)
            if satisfied:
                if depend[0] == "!": icon = gtk.STOCK_NO
                else: icon = gtk.STOCK_YES
            else:
                if depend[0] == "!": icon = gtk.STOCK_YES
                else: icon = gtk.STOCK_NO
            # only show base dependenciy layer, or unfilled dependencies
            if icon == gtk.STOCK_NO or base == None:
                if parent != None:
                    if parent_icon == '': continue
                    if icon == gtk.STOCK_NO and parent_icon == gtk.STOCK_YES:
                        self.set_value(base_iter, 1, depends_view.render_icon(gtk.STOCK_NO,
                                       size = gtk.ICON_SIZE_MENU, detail = None))
                        if base != None:
                            base_iter = self.insert_before(base, None)
                            self.set_value(base_iter, 0, parent)
                            dep_before = base_iter
                depend_iter = self.insert_before(dep_before, None)
                self.set_value(depend_iter, 0, depend)
                self.set_value(depend_iter, 3, satisfied)
                self.set_value(depend_iter, 1, 
                                    depends_view.render_icon(icon,
                                                             size = gtk.ICON_SIZE_MENU,
                                                             detail = None))
                # get depname from depend:
                # The get_text stuff above converted this to unicode, which gives portage headaches.
                # So we have to convert this with str()
                depname = str(portagelib.get_full_name(depend))
                if not depname: continue
                pack = portagelib.Package(depname)
                self.set_value(depend_iter, 2, pack)
                if icon != gtk.STOCK_YES:
                    #dprint("Dependency %s not found... recursing..." % str(depname))
                    if depname not in self.depends_list:
                        self.depends_list.append(depname)
                        depends = (pack.get_properties().depend.split() +
                                   pack.get_properties().rdepend.split())
                        if depends:
                            self.add_depends_to_tree(depends, depends_view, depend_iter)
            else:
                #dprint("dependency '%s' skipped" % depend)
                pass


#~ return depend, op
        #~ else:
            #~ return depend, None

    #~ def is_dep_satisfied(self, installed_ebuild, dep_ebuild, operator = "="):
        #~ """ Returns installed_ebuild <operator> dep_ebuild """
        #~ retval = False
        #~ ins_ver = portagelib.get_version(installed_ebuild)
        #~ dep_ver = portagelib.get_version(dep_ebuild)
        #~ # extend to normal comparison operators in case they aren't
        #~ if operator == "=": operator = "=="
        #~ if operator == "!": operator = "!="
        #~ # determine the retval
        #~ if operator == "==": retval = ins_ver == dep_ver
        #~ elif operator == "<=":  retval = ins_ver <= dep_ver
        #~ elif operator == ">=": retval = ins_ver >= dep_ver
        #~ elif operator == "!=": retval = ins_ver != dep_ver
        #~ elif operator == "<": retval = ins_ver < dep_ver
        #~ elif operator == ">": retval = ins_ver > dep_ver
        #~ # return the result of the operation
        #~ return retval

    def fill_depends_tree(self, treeview, package):
        """Fill the dependencies tree for a given ebuild"""
        #dprint("DEPENDS: Updating deps tree for " + package.get_name())
        ebuild = package.get_default_ebuild()
        ##depends = portagelib.get_property(ebuild, "DEPEND").split()
        depends = (package.get_properties().depend.split() +
                   package.get_properties().rdepend.split())
        self.clear()
        if depends:
            #dprint(depends)
            self.depends_list = []
            self.add_depends_to_tree(depends, treeview)
        else:
            parent_iter = self.insert_before(None, None)
            self.set_value(parent_iter, 0, _("None"))
        treeview.set_model(self)
