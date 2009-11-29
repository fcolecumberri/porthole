#!/usr/bin/env python

'''
    Porthole Depends TreeModel
    Calculates and stores package dependency information

    Copyright (C) 2003 - 2009 Fredrik Arnerup, Daniel G. Taylor,
    Brian Dolbec, Tommy Iorns

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

import gtk, gobject, string
from gettext import gettext as _

from porthole.utils import debug
from porthole import backends
portage_lib = backends.portage_lib
from porthole.backends.utilities import get_reduced_flags, slot_split, use_required_split, get_sync_info
from porthole import db
from porthole.packagebook.depends import  atomize_depends_list, get_depends




class DependsTree(gtk.TreeStore):
    """Calculate and display dependencies in a treeview"""
    def __init__(self):
        """Initialize the TreeStore object"""
        gtk.TreeStore.__init__(self, gobject.TYPE_STRING,   # depend name
                                gtk.gdk.Pixbuf,                      # icon to display
                                gobject.TYPE_PYOBJECT,   # package object
                                gobject.TYPE_BOOLEAN,    # is_satisfied
                                gobject.TYPE_STRING,        # package name
                                gobject.TYPE_STRING,        # installed version
                                gobject.TYPE_STRING,        # latest recommended version
                                gobject.TYPE_STRING,       # keyword
                                gobject.TYPE_STRING)        # use flags required to be enabled
        self.column = {
            "depend" : 0,
            "icon" : 1,
            "package" : 2,
            "satisfied" : 3,
            "name" : 4,
            "installed" : 5,
            "latest" : 6,
            "keyword":7,
            "required_use":8
        }
        self.dep_depth = 0
        self.parent_use_flags = {}
        
    def parse_depends_list(self, depends_list, parent = None):
        """Read through the depends list and order it nicely
           Returns a list of (parent, dep, satisfied) for each dep"""
        new_list = []
        use_list = []
        ops = ""
        using_list=False
        for dep in depends_list:
            #debug.dprint(dep)
            if dep[-1] == "?":
                if dep[0] != "!":
                    parent = _("Using ") + dep[:-1]
                    using_list=True
                else:
                    parent = _("Not Using ") + dep[1:-1]
            else:
                if dep not in ["(", ")", ":", "||"]:
                    satisfied = portage_lib.get_installed(dep)
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
                    

    def add_atomized_depends_to_tree(self, atomized_depends_list, depends_view,
                                     parent_iter=None, add_satisfied=1, ebuild = None, is_new_child = False):
        """Add atomized dependencies to the tree"""
        #debug.dprint(" * DependsTree: add_atomized_depends_list(): new depth level = " + str(self.dep_depth))
        if ebuild and is_new_child:
            self.parent_use_flags[self.dep_depth] = get_reduced_flags(ebuild)
            #debug.dprint(" * DependsTree: add_atomized_depends_list(): parent_use_flags = reduced: " + str(self.parent_use_flags[self.dep_depth]))
        elif is_new_child:
            self.parent_use_flags[self.dep_depth] = portage_lib.settings.SystemUseFlags
            #debug.dprint(" * DependsTree: add_atomized_depends_list(): parent_use_flags = system only")
        for atom in atomized_depends_list:
            dep_atomized_list = []
            satisfied = atom.is_satisfied(self.parent_use_flags[self.dep_depth])
            if satisfied:
                icon = gtk.STOCK_YES
                add_kids = 0
            else:
                icon = gtk.STOCK_NO
                add_kids = 1
            
            if add_satisfied or not satisfied: # then add deps to treeview
                #debug.dprint("DependsTree: atom '%s', type '%s', satisfied '%s'" % (atom.get_depname(), atom.type, satisfied))
                iter = self.insert_before(parent_iter, None)
                if atom.type == 'USING':
                    text = _("Using %s") % atom.useflag
                    if satisfied == -1: icon = gtk.STOCK_REMOVE # -1 ==> irrelevant
                    add_kids = -1 # add kids but don't expand unsatisfied deps
                    add_satisfied = 1
                elif atom.type == 'NOTUSING':
                    text = _("Not Using %s") % atom.useflag
                    if satisfied == -1: icon = gtk.STOCK_REMOVE # -1 ==> irrelevant
                    add_kids = -1 # add kids but don't expand unsatisfied deps
                    add_satisfied = 1
                elif atom.type =='DEP':
                    text = atom.get_depname()
                    if not satisfied and self.dep_depth < 4:
                        add_kids = 1
                elif atom.type == 'BLOCKER':
                    text = "!" + atom.get_depname()
                    if not satisfied: icon = gtk.STOCK_DIALOG_WARNING
                elif atom.type == 'OPTION':
                    text = _("Any of:")
                    add_kids = -1 # add kids but don't expand unsatisfied deps
                    add_satisfied = 1
                elif atom.type == 'GROUP':
                    text = _("All of:")
                    add_kids = -1 # add kids but don't expand unsatisfied deps
                    add_satisfied = 1
                elif atom.type =='REVISIONABLE':
                    text = '~' + atom.get_depname()
                    if not satisfied and self.dep_depth < 4:
                        add_kids = 1
                
                if icon:
                    self.set_value(iter, self.column["icon"], depends_view.render_icon(icon,
                                      size = gtk.ICON_SIZE_MENU, detail = None))
                self.set_value(iter, self.column["depend"], text)
                self.set_value(iter, self.column["satisfied"], bool(satisfied))
                self.set_value(iter, self.column["required_use"], atom.get_required_use())
                if atom.type in ['DEP', 'BLOCKER', 'REVISIONABLE']:
                    depname = portage_lib.get_full_name(atom.name)
                    if not depname:
                        debug.dprint(" * DependsTree: add_atomized_depends_list(): No depname found for '%s'" % atom.name or atom.useflag)
                        continue
                    #pack = Package(depname)
                    pack = db.db.get_package(depname)
                    self.set_value(iter, self.column["package"], pack)
                #debug.dprint("DependsTree: add_atomized_depends_list(): add_kids = " \
                #                            +str(add_kids) + " add_satisfied = " + str(add_satisfied))
                # add kids if we should
                if add_kids < 0 and add_satisfied != -1:
                    self.add_atomized_depends_to_tree(atom.children, depends_view, iter, add_kids)
                elif add_kids  > 0 and not satisfied and self.dep_depth <= 4:
                    # be carefull of depth
                    best,keyworded,masked  = portage_lib.get_dep_ebuild(atom.__repr__())
                    #debug.dprint("DependsTree: add_atomized_depends_list(): results = " + ', '.join([best,keyworded,masked]))
                    # get the least unstable dep_ebuild that satisfies the dep
                    if best != '':
                        dep_ebuild = best
                    elif keyworded != '':
                        dep_ebuild = keyworded
                    else:
                        dep_ebuild = masked
                    if dep_ebuild:
                        dep_deps = get_depends(pack, dep_ebuild)
                        dep_atomized_list = atomize_depends_list(dep_deps)
                        if dep_atomized_list == None: dep_atomized_list = []
                        #debug.dprint("DependsTree: add_atomized_depends_list(): DEP new atomized_list for: " \
                        #                                + atom.get_depname() + ' = ' + str(dep_atomized_list) + ' ' + dep_ebuild)
                        self.dep_depth += 1
                        self.add_atomized_depends_to_tree(dep_atomized_list, depends_view, iter, add_kids, ebuild = dep_ebuild, is_new_child = True )
                        self.dep_depth -= 1
                    #del best,keyworded,masked

    def fill_depends_tree(self, treeview, package, ebuild):
        """Fill the dependencies tree for a given ebuild"""
        #debug.dprint("DependsTree: Updating deps tree for " + package.name)
        #ebuild = package.get_default_ebuild()
        ##depends = portage_lib.get_property(ebuild, "DEPEND").split()
        depends = get_depends(package, ebuild)
        self.clear()
        if depends:
            #debug.dprint("DependsTree: depends = %s" % depends)
            # remove !bootstrap? entries:
            x = 0
            while x < len(depends):
                if depends[x] == "!bootstrap?":
                    depends.pop(x) # remove !bootstrap?
                    depends.pop(x) # remove (
                    level = 1
                    while level:
                        if depends[x] == "(": level += 1
                        if depends[x] == ")": level -= 1
                        depends.pop(x)
                else: x += 1
            #debug.dprint("DependsTree: reduced depends = " + str(depends))
            self.depends_list = []
            #self.add_depends_to_tree(depends, treeview)
            atomized_depends = atomize_depends_list(depends)
            #debug.dprint(atomized_depends)
            self.add_atomized_depends_to_tree(atomized_depends, treeview, ebuild = ebuild, is_new_child = True)
        else:
            parent_iter = self.insert_before(None, None)
            self.set_value(parent_iter, self.column["depend"], _("None"))
        treeview.set_model(self)
