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
from porthole.backends.utilities import get_reduced_flags, slot_split, \
    use_required_split, get_sync_info
from porthole import db
from porthole.packagebook.depends import  Depends, LAZYNAME

# used for timing some sections of code
#import datetime  


class DependsTree(gtk.TreeStore):
    """Calculate and display dependencies in a treeview"""
    def __init__(self, populate_info):
        """Initialize the TreeStore object
        
        @param populate_info: function supplied to add aditional info to the treeview row
        """
        gtk.TreeStore.__init__(self, 
                gobject.TYPE_STRING,       # depend name
                gtk.gdk.Pixbuf,            # icon to display
                gobject.TYPE_PYOBJECT,     # package object
                gobject.TYPE_BOOLEAN,      # is_satisfied
                gobject.TYPE_STRING,       # package name
                gobject.TYPE_STRING,       # installed version
                gobject.TYPE_STRING,       # latest recommended version
                gobject.TYPE_STRING,       # keyword
                gobject.TYPE_STRING,       # use flags required to be enabled
                gobject.TYPE_PYOBJECT      # atom key
        )
       
        self.column = {
            "depend" : 0,
            "icon" : 1,
            "package" : 2,
            "satisfied" : 3,
            "name" : 4,
            "installed" : 5,
            "latest" : 6,
            "keyword":7,
            "required_use":8,
            "atom_key":9
        }
        self.populate_info = populate_info
        self.dep_depth = 0
        self.max_depth = 1
        self.parent_use_flags = {}
        self.dep_parser = Depends()
        self.dep_parser.flags.append("!bootstrap?")


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


    def _add_list(self, atomized_depends_list, depends_view,
            parent_iter=None, add_satisfied=1, ebuild = None, is_new_child = False, 
            depth=0, dep_depth=0):
        """Add atomized dependencies to the tree"""
        #debug.dprint(" * DependsTree: add_atomized_depends_list() 110: new depth level = "
            #+ str(depth))
        if ebuild and is_new_child:
            self.parent_use_flags[depth] = get_reduced_flags(ebuild)
            #debug.dprint(" * DependsTree: add_atomized_depends_list():" +
                #" parent_use_flags = reduced: " + str(self.parent_use_flags[depth]))
        elif is_new_child: # and atomized_depends_list[0].mytype not in ['LAZY']:
            self.parent_use_flags[depth] = portage_lib.settings.SystemUseFlags
            #debug.dprint(" * DependsTree: add_atomized_depends_list(): 122, is_new_child " +
            #    " parent_use_flags = system only")
        for atom in atomized_depends_list:
            satisfied = atom.is_satisfied(self.parent_use_flags[depth])
            
            if add_satisfied or not satisfied: # then add deps to treeview
                #debug.dprint(
                #    "DependsTree:_add_list(); 129 atom '%s', mytype '%s', satisfied '%s'"
                #        % (atom.get_depname(), atom.mytype, satisfied))
                if satisfied == []:
                    satisfied = False
                iter = self.insert_before(parent_iter, None)
                add_kids, add_satisfied = self.update_row(iter, atom, satisfied,
                    add_satisfied, depends_view)
                #debug.dprint(
                #    "DependsTree:_add_list(); 136 atom '%s', mytype '%s', add_kids=%s satisfied '%s'"
                #    % (atom.get_depname(), atom.mytype, add_kids, satisfied))
                self.update_kids(atom, add_kids, add_satisfied, satisfied, depth,
                    dep_depth, depends_view, iter)
        return

    def update_row(self, iter, atom, satisfied, add_satisfied, depends_view):
        """Update the treeview row @ iter with info for atom
        
        @param iter: a treeview iter set to the row to update
        @param atom: a DependAtom instance to display info for
        """
        # establish some defaults
        if satisfied:
            icon = gtk.STOCK_YES
            add_kids = 0
        else:
            icon = gtk.STOCK_NO
            add_kids = 1
        text = atom.get_depname()
        add_kids, add_satisfied, icon = \
            getattr(self, "_%s_" %atom.mytype)(satisfied, add_satisfied, icon)
        
        if icon:
            self.set_value(iter, self.column["icon"], depends_view.render_icon(icon,
                              size = gtk.ICON_SIZE_MENU, detail = None))
        self.set_value(iter, self.column["depend"], text)
        self.set_value(iter, self.column["satisfied"], bool(satisfied))
        self.set_value(iter, self.column["required_use"], atom.get_required_use())
        self.set_value(iter, self.column["atom_key"], atom.key)
        if atom.mytype in ['DEP', 'BLOCKER', 'REVISIONABLE']:
            pack = self._get_package(atom)
            self.set_value(iter, self.column["package"], pack)
            # treeview's populate_info() callback
            gobject.idle_add(self.populate_info,self, self.get_path(iter), iter)
        return add_kids, add_satisfied

    def update_kids(self, atom, add_kids, add_satisfied, satisfied,
                    depth, dep_depth, depends_view, iter):
        #debug.dprint("DependsTree: update_kids() 176: add_kids = "  + str(add_kids) +
        #    " add_satisfied = " + str(add_satisfied) + " depth=%d, dep-depth=%d"
        #    %(depth, dep_depth))
        # add kids if we should
        if add_kids < 0 and add_satisfied != -1: 
            if depth <= self.max_depth:
                #debug.dprint(" * DependsTree: update_kids():182 adding kids")
                self._add_list(atom.children, depends_view, iter,
                    add_kids, is_new_child = True, depth=depth+1, )
                #
            else:
                #debug.dprint(" * DependsTree: update_row():187 adding lazy kids, parent=%s"
                #    %(atom.mytype+atom.useflag+atom.atom+atom.parent))
                self._add_lazy(atom, depends_view, iter, add_kids=0, depth=depth)
        elif add_kids  > 0 and not satisfied and depth <= self.max_depth:
            #debug.dprint(" * DependsTree: update_kids():195 adding kids")
            self._add_kids(atom, depends_view, iter, add_kids, depth,
                self.get_value(iter, self.column["package"]), dep_depth)
        elif add_kids > 0 and not satisfied:
            #debug.dprint(" * DependsTree: update_kids(): 195 adding lazy kids")
            self._add_lazy(atom, depends_view, iter, add_kids, depth)
        return


    def _add_kids(self, atom, depends_view, iter, add_kids, 
            depth, pack, dep_depth):
        """Adds a dependencies children to the tree model
        """
        dep_ebuild = self._get_ebuild(atom)
        # be carefull of depth
        if dep_ebuild:
            dep_deps = self.dep_parser.get_depends(pack, dep_ebuild)
            dep_atomized_list = self.dep_parser.parse(dep_deps)
            if dep_atomized_list == None: dep_atomized_list = []
            #debug.dprint("DependsTree: _add_kids(): new atomized_list for: " 
            #    +atom.get_depname()+' = '+str(dep_atomized_list)+' '+str(dep_ebuild))
            self._add_list(dep_atomized_list, depends_view, iter,
                add_kids, ebuild = dep_ebuild, is_new_child = True, depth=depth+1,
                dep_depth=dep_depth)
        else:
            debug.dprint("DependsTree: _add_kids(): Failed to get dep_ebuild for " +
                "atom=%s" %(atom.atom))
        return


    def _add_lazy(self, atom, depends_view, iter, add_kids, depth):
        """Add a lazy dependency placeholder to be filled in when it's parent
        tree node is expanded
        """
        if atom.mytype in ["LAZY", "OPTION", "GROUP", "USING", " NOTUSING"]:
            dep_ebuild = ' '
        else:
            dep_ebuild = self._get_ebuild(atom)
        # be carefull of depth
        if dep_ebuild:
            key = self.dep_parser.cache.add_lazy(atom)
            lazy_atom = self.dep_parser.cache.get(key)
            #debug.dprint("DependsTree: _add_lazy():key=%s, lazy_atom=%s"
                #%(key,str(lazy_atom)))
            kid_iter = self.insert_before(iter, None)
            add_kids, add_satisfied = self.update_row(kid_iter, lazy_atom, satisfied=0,
                add_satisfied=1, depends_view= depends_view)
            #self._add_list(mylist, depends_view, iter,
            #    add_kids, ebuild=dep_ebuild, is_new_child=True, depth=depth+1)
        else:
            debug.dprint("DependsTree: _add_lazy(): Failed to get dep_ebuild for " +
                "atom=%s" %(atom.atom))
        return


    def _get_ebuild(self, atom):
        """Get the least unstable dep_ebuild that satisfies the dep
        """
        
        if not atom.atom:
            debug.dprint("DependsTree:  _get_ebuild(): atom.atom = Null for atom:%s"
                %atom.__repr__())
            return None
        best, keyworded, masked  = portage_lib.get_dep_ebuild(atom.atom) #__repr__())
        #debug.dprint("DependsTree:  _get_ebuild(): results = " + \
            #', '.join([best,keyworded,masked]))
        # 
        if best != '':
            dep_ebuild = best
        elif keyworded != '':
            dep_ebuild = keyworded
        else:
            dep_ebuild = masked
        return dep_ebuild


    def expand_lazy(self, treeview, iter, path):
        #debug.dprint("DependsTree:  expand_lazy(): activated by  'test-expand-row'")
        # first find out if there are already kids to expand
        kid_iter = self.iter_children(iter)
        if kid_iter:
            # determine if it a lazy atom
            if self.get_value(kid_iter, self.column["depend"]) != LAZYNAME:
                return True
            else:
                lazy_key = self.get_value(kid_iter, self.column["atom_key"])
                # delete the lazy atom
                valid = self.remove(kid_iter)
                if valid:
                    debug.dprint("DependsTree:  expand_lazy(); kid_iter still" +
                        " valid after lazy_atom removed")
                self.dep_parser.cache.remove(lazy_key)
        # get the atom to expand
        key = self.get_value(iter, self.column["atom_key"])
        atom = self.dep_parser.cache.get(key)
        # check if there are kids already populated
        if atom.children:
            self._add_list(atom.children, treeview, parent_iter=iter,
                is_new_child = True)
        else:
            pack = self._get_package(atom)
            self._add_kids(atom=atom, depends_view=treeview, iter=iter,
                add_kids=True, depth=0, pack=pack, dep_depth=0)
        return True

    def fill_depends_tree(self, treeview, package, ebuild):
        """Fill the dependencies tree for a given ebuild"""
        #debug.dprint("DependsTree: Updating deps tree for " + package.name)
        # first reset the DepCache
        #start = datetime.datetime.now() #.microsecond
        self.dep_parser.cache.reset()
        depends = self.dep_parser.get_depends(package, ebuild)
        self.clear()
        if depends:
            #debug.dprint("DependsTree: depends = %s" % depends)
            self.depends_list = []
            #self.add_depends_to_tree(depends, treeview)
            #debug.dprint("DependsTree: calling self.dep_parser.parse();" +
                #" ebuild=%s reduced depends = %s " 
            #        % (ebuild, str(depends)))
            atomized_depends = self.dep_parser.parse(depends)
            #end = datetime.datetime.now() #.microsecond
            #debug.dprint(atomized_depends)
            self._add_list(atomized_depends, treeview,
                ebuild = ebuild, is_new_child = True)
            #end2 = datetime.datetime.now() #.microsecond
        else:
            parent_iter = self.insert_before(None, None)
            self.set_value(parent_iter, self.column["depend"], _("None"))
            #end = end2 = datetime.datetime.now() #.microsecond
        treeview.set_model(self)
        #debug.dprint("DependsTree: Timing self.dep_parser; ebuild=%s time= %s"
            #% (ebuild, end-start))
        #debug.dprint("DependsTree: Timing self.dep_parser; complete parse & tree," +
            #" time= %s" % (end2-start))

    def _get_package(self, atom):
        name = portage_lib.split_atom_pkg(atom.name)[0]
        #debug.dprint(" * DependsTree: _get_package(): name=" + name)
        if not name:
            debug.dprint(" * DependsTree: _get_package():" +
                "No depname found for '%s'" % atom.name or atom.useflag)
            return None
        return db.db.get_package(name)


    def _USING_(self, satisfied, add_satisfied, icon):
        """ atom.mytype == 'USING'
        @rtype (add_kids, add_satisfied, icon)"""
        #add_kids = -1 # add kids but don't expand unsatisfied deps
        #add_satisfied = 1
        if satisfied == -1: 
            return -1, 1, gtk.STOCK_REMOVE # -1 ==> irrelevant
        elif not satisfied:
            return -1, 1, gtk.STOCK_NO
        return -1, 1, gtk.STOCK_YES


    def _NOTUSING_(self, satisfied, add_satisfied, icon):
        """ atom.mytype == 'NOTUSING'
        @rtype (add_kids, add_satisfied, icon)"""
        #add_kids = -1 # add kids but don't expand unsatisfied deps
        #add_satisfied = 1
        if satisfied == -1:
            return -1, 1, gtk.STOCK_REMOVE # -1 ==> irrelevant
        return -1, 1, gtk.STOCK_YES


    def _DEP_(self, satisfied, add_satisfied, icon):
        """ atom.mytype =='DEP'
        @rtype (add_kids, add_satisfied, icon)"""
        if not satisfied: #and self.dep_depth < self.max_depth:
            return 1, 1,  gtk.STOCK_NO
        return 0, 1 ,  gtk.STOCK_YES


    def _REVISIONABLE_(self, add_satisfied, satisfied, icon):
        """ atom.mytype =='REVISIONABLE'
        @rtype (add_kids, add_satisfied, icon)"""
        if not satisfied: # and self.dep_depth < 4:
            return 1, add_satisfied, icon
        return 0, add_satisfied, icon


    def _BLOCKER_(self, satisfied, add_satisfied, icon):
        """ atom.mytype == 'BLOCKER'
        @rtype (add_kids, add_satisfied, icon)"""
        if not satisfied:
            return 0, add_satisfied, gtk.STOCK_DIALOG_WARNING
        return 0, add_satisfied, gtk.STOCK_YES


    def _OPTION_(self, satisfied, add_satisfied, icon):
        """ atom.mytype == 'OPTION'
        @rtype (add_kids, add_satisfied, icon)"""
        return -1, 1, icon


    def _GROUP_(self, satisfied, add_satisfied, icon):
        """ atom.mytype == 'GROUP'
        @rtype (add_kids, add_satisfied, icon)"""
        return -1, 1, icon


    def _LAZY_(self, satisfied, add_satisfied, icon):
        """ atom.mytype == 'LAZY'
        @rtype (add_kids, add_satisfied, icon)"""
        return 0, 0, gtk.STOCK_NO
