#!/usr/bin/env python

'''
    Porthole Depends TreeModel
    Calculates and stores package dependency information

    Copyright (C) 2003 - 2006 Fredrik Arnerup, Daniel G. Taylor,
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
import utils.debug
from gettext import gettext as _

import backends
portage_lib = backends.portage_lib

from db.package import Package
import db

class DependAtom:
    """Dependency Atom Class.
    Important methods: __repr__(), __eq__(), is_satisfied().
    """
    def __init__(self, parent):
        self.type = ''
        self.children = []
        self.parent = parent
        self.useflag = ''
        self.name = ''
        self.complete = False
    
    def __repr__(self): # called by the "print" function
        """Returns a human-readable string representation of the DependAtom
        (used by the "print" statement)."""
        if self.type == 'DEP': return self.name
        elif self.type == 'BLOCKER': return '!' + self.name
        elif self.type == 'OPTION': prefix = '||'
        elif self.type == 'GROUP': prefix = ''
        elif self.type == 'USING': prefix = self.useflag + '?'
        elif self.type == 'NOTUSING': prefix = '!' + self.useflag + '?'
        elif self.type == 'REVISIONABLE': return '~' + self.name
        else: return ''
        if self.children:
            bulk = ', '.join([kid.__repr__() for kid in self.children])
            return ''.join([prefix,'[',bulk,']'])
        elif prefix: return ''.join([prefix,'[]'])
        else: return ''
    
    def __eq__(self, test_atom): # "atomA == atomB" <==> "atomA.__eq__(atomB)"
        """Returns True if the test_atom is equivalent to self
        (used by the statement "atomA == atomB")"""
        if (not isinstance(test_atom, DependAtom)
                or self.type != test_atom.type
                or self.name != test_atom.name
                or self.useflag != test_atom.useflag
                or self.children != test_atom.children): # children will recurse
            return False
        else: return True
    
    def is_satisfied(self, use_flags):
        """Currently returns an object of variable type, indicating whether
        this dependency is satisfied.
        Returns -1 if being satisfied is irrelevant (e.g. use flag for a
        "USING" DependAtom is not set). Otherwise, the return value can be
        evaluated as True if the dep is satisfied, False if unsatisfied."""
        if self.type == 'DEP': return portage_lib.get_installed(self.name)
        elif self.type == 'BLOCKER': return not portage_lib.get_installed(self.name)
        elif self.type == 'OPTION': # nonempty if any child is satisfied
            satisfied = []
            for child in self.children:
                a = child.is_satisfied(use_flags)
                if a: satisfied.append(a)
            return satisfied
        elif self.type == 'GROUP': # 0 if not satisfied, 1 if satisfied
            satisfied = 1
            for child in self.children:
                if not child.is_satisfied(use_flags): satisfied = 0
            return satisfied
        elif self.type == 'USING': # -1 if not using, 0 if not satisfied, 1 if satisfied
            if self.useflag in use_flags:
                satisfied = 1
                for child in self.children:
                    if not child.is_satisfied(use_flags): satisfied = 0
            else: satisfied = -1
            return satisfied
        elif self.type == 'NOTUSING': # -1 if using, 0 if not satisfied, 1 if satisfied
            if self.useflag not in use_flags:
                satisfied = 1
                for child in self.children:
                    if not child.is_satisfied(use_flags): satisfied = 0
            else: satisfied = -1
            return satisfied
        elif self.type == 'REVISIONABLE': # nonempty if is satisfied
            return portage_lib.get_installed('~' + self.name)
            

class DependsTree(gtk.TreeStore):
    """Calculate and display dependencies in a treeview"""
    def __init__(self):
        """Initialize the TreeStore object"""
        gtk.TreeStore.__init__(self, gobject.TYPE_STRING,   # depend name
                                gtk.gdk.Pixbuf,                   # icon to display
                                gobject.TYPE_PYOBJECT,     # package object
                                gobject.TYPE_BOOLEAN,     # is_satisfied
                                gobject.TYPE_STRING,        # package name
                                gobject.TYPE_STRING,        # installed version
                                gobject.TYPE_STRING,        # latest recommended version
                                gobject.TYPE_STRING)        # keyword
        self.column = {
            "depend" : 0,
            "icon" : 1,
            "package" : 2,
            "satisfied" : 3,
            "name" : 4,
            "installed" : 5,
            "latest" : 6,
            "keyword":7,
            "atom": 8
        }
        self.use_flags = portage_lib.get_portage_environ("USE").split()
        self.dep_depth = 0
        
    def parse_depends_list(self, depends_list, parent = None):
        """Read through the depends list and order it nicely
           Returns a list of (parent, dep, satisfied) for each dep"""
        new_list = []
        use_list = []
        ops = ""
        using_list=False
        for dep in depends_list:
            #utils.debug.dprint(dep)
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
                                     parent_iter=None, add_satisfied=1):
        """Add atomized dependencies to the tree"""
        for atom in atomized_depends_list:
            dep_atomized_list = []
            satisfied = atom.is_satisfied(self.use_flags)
            if satisfied:
                icon = gtk.STOCK_YES
                add_kids = 0
            else:
                icon = gtk.STOCK_NO
                add_kids = 1
            
            if add_satisfied or not satisfied: # then add deps to treeview
                #utils.debug.dprint("DependsTree: atom '%s', type '%s', satisfied '%s'" % (atom.name, atom.type, satisfied))
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
                    text = atom.name
                    if not satisfied and self.dep_depth < 4:
                        add_kids = 1
                elif atom.type == 'BLOCKER':
                    text = "!" + atom.name
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
                    text = '~' + atom.name
                    if not satisfied and self.dep_depth < 4:
                        add_kids = 1
                
                if icon:
                    self.set_value(iter, self.column["icon"], depends_view.render_icon(icon,
                                      size = gtk.ICON_SIZE_MENU, detail = None))
                self.set_value(iter, self.column["depend"], text)
                self.set_value(iter, self.column["satisfied"], bool(satisfied))
                if atom.type in ['DEP', 'BLOCKER', 'REVISIONABLE']:
                    depname = portage_lib.get_full_name(atom.name)
                    if not depname:
                        utils.debug.dprint(" * DependsTree: add_atomized_depends_list(): No depname found for '%s'" % atom.name or atom.useflag)
                        continue
                    #pack = Package(depname)
                    pack = db.db.get_package(depname)
                    self.set_value(iter, self.column["package"], pack)
                #utils.debug.dprint("DependsTree: add_atomized_depends_list(): add_kids = " \
                #                            +str(add_kids) + " add_satisfied = " + str(add_satisfied))
                # add kids if we should
                if add_kids < 0 and add_satisfied != -1:
                    self.add_atomized_depends_to_tree(atom.children, depends_view, iter, add_kids)
                elif add_kids  > 0 and not satisfied and self.dep_depth <= 4:
                    # be carefull of depth
                    best,keyworded,masked  = portage_lib.get_dep_ebuild(atom.__repr__())
                    #utils.debug.dprint("DependsTree: add_atomized_depends_list(): results = " + ', '.join([best,keyworded,masked]))
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
                        #utils.debug.dprint("DependsTree: add_atomized_depends_list(): DEP new atomized_list for: " \
                        #                                + atom.name + ' = ' + str(dep_atomized_list) + ' ' + dep_ebuild)
                        self.dep_depth += 1
                        self.add_atomized_depends_to_tree(dep_atomized_list, depends_view, iter, add_kids)
                        self.dep_depth -= 1
                    #del best,keyworded,masked

    def fill_depends_tree(self, treeview, package, ebuild):
        """Fill the dependencies tree for a given ebuild"""
        utils.debug.dprint("DependsTree: Updating deps tree for " + package.get_name())
        #ebuild = package.get_default_ebuild()
        ##depends = portage_lib.get_property(ebuild, "DEPEND").split()
        depends = get_depends(package, ebuild)
        self.clear()
        if depends:
            #utils.debug.dprint("DependsTree: depends = %s" % depends)
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
            #utils.debug.dprint("DependsTree: reduced depends = " + str(depends))
            self.depends_list = []
            #self.add_depends_to_tree(depends, treeview)
            atomized_depends = atomize_depends_list(depends)
            #utils.debug.dprint(atomized_depends)
            self.add_atomized_depends_to_tree(atomized_depends, treeview)
        else:
            parent_iter = self.insert_before(None, None)
            self.set_value(parent_iter, self.column["depend"], _("None"))
        treeview.set_model(self)

def atomize_depends_list(depends_list, parent = None):
    """Takes a list of the form:
    portage.portdb.aux_get(<ebuild>, ["DEPEND"]).split()
    and arranges it into a list of nested list-like DependAtom()s.
    if more closing brackets are encountered than opening ones then it
    will return, meaning we can recursively pass the unparsed part of the
    list back to ourselves...
    """
    atomized_list = []
    temp_atom = None
    while depends_list:
        item = depends_list[0]
        #utils.debug.dprint("DependsTree: atomize_depends_list();298 start of while loop, item = " + str(item) + ", parent = " +str(parent))
        if item.startswith("||"):
            temp_atom = DependAtom(parent)
            temp_atom.type = 'OPTION'
            if item != "||":
                depends_list[0] = item[2:]
                #utils.debug.dprint("DependsTree: atomize_depends_list();304 item != ||, item[2:] = " + str(item[2:]) + ", parent = " +str(parent))
            else:
                depends_list.pop(0)
            item = depends_list[0]
            #utils.debug.dprint("DependsTree: atomize_depends_list();308 new item = " + str(item) + ", parent = " +str(parent))
        elif item.endswith("?"):
            temp_atom = DependAtom(parent)
            if item.startswith("!"):
                temp_atom.type = 'NOTUSING'
                temp_atom.useflag = item[1:-1]
            else:
                temp_atom.type = 'USING'
                temp_atom.useflag = item[:-1]
            depends_list.pop(0)
            item = depends_list[0]
        if item.startswith("("):
            #utils.debug.dprint("DependsTree: atomize_depends_list();320 item.startswith '(', item = " + item + ", parent = " +str(parent) \
            #                                + ", temp_atom = " +str(temp_atom))
            if temp_atom is None: # two '(' in a row. Need to create temp_atom
                #utils.debug.dprint("DependsTree: atomize_depends_list();323 item.startswith '(', new temp_atom for parent: " +str(parent))
                temp_atom = DependAtom(parent)
                temp_atom.type = 'GROUP'
            if item != "(":
                depends_list[0] = item[1:]
                #utils.debug.dprint("DependsTree: atomize_depends_list();328 item != '(': new depends_list[0]= " +str(depends_list[0]))
            else:
                #utils.debug.dprint("DependsTree: atomize_depends_list();330 next recursion level, depends_list: "+str(depends_list))
                #utils.debug.dprint("DependsTree: atomize_depends_list();331 next recursion level, temp_atom: "+str(temp_atom))
                group, depends_list = split_group(depends_list)
                temp_atom.children = atomize_depends_list(group, temp_atom)
                if not filter(lambda a: temp_atom == a, atomized_list):
                # i.e. if temp_atom is not any atom in atomized_list.
                # This is checked by calling DependAtom.__eq__().
                    #utils.debug.dprint("DependsTree: atomize_depends_list();337 ')'-1, atomized_list.append(temp_atom) = " + str(temp_atom) + ", parent = " +str(parent))
                    atomized_list.append(temp_atom)
                temp_atom = None
                continue
                #utils.debug.dprint("DependsTree: atomize_depends_list();341 item = '(': new depends_list[0]= " +str(depends_list[0]))
            #utils.debug.dprint("DependsTree: atomize_depends_list();342 next recursion level, depends_list: "+str(depends_list))
            #utils.debug.dprint("DependsTree: atomize_depends_list();343 next recursion level, temp_atom: "+str(temp_atom))
            temp_atom.children = atomize_depends_list(depends_list, temp_atom)
            if not filter(lambda a: temp_atom == a, atomized_list):
            # i.e. if temp_atom is not any atom in atomized_list.
            # This is checked by calling DependAtom.__eq__().
                #utils.debug.dprint("DependsTree: atomize_depends_list();348 ')'-1, atomized_list.append(temp_atom) = " + str(temp_atom) + ", parent = " +str(parent))
                atomized_list.append(temp_atom)
            temp_atom = None
            continue
        elif item.startswith(")"):
            if item != ")":
                depends_list[0] = item[1:]
            else:
                depends_list.pop(0)
                #utils.debug.dprint("DependsTree: atomize_depends_list();357 finished recursion level, returning atomized list") 
            return atomized_list
        else: # hopefully a nicely formatted dependency
            if filter(lambda a: a in item, ['(', '|', ')', '?']):
                utils.debug.dprint(" *** DEPENDS: atomize_depends_list: ILLEGAL ITEM!!! " + \
                    "Please report this to the authorities. (item = %s)" % item)
            temp_atom = DependAtom(parent)
            if item.startswith("!"):
                #utils.debug.dprint("DependsTree: atomize_depends_list();365 found a BLOCKER dep: " + item)
                temp_atom.type = "BLOCKER"
                temp_atom.name = item[1:]
            elif item.startswith('~'):
                #utils.debug.dprint("DependsTree: atomize_depends_list();369 found a REVISIONABLE dep: " + item)
                temp_atom.type = "REVISIONABLE"
                temp_atom.name = item[1:]
            else:
                #utils.debug.dprint("DependsTree: atomize_depends_list();373 found a DEP dep: " + item)
                temp_atom.type = "DEP"
                temp_atom.name = item
            if not filter(lambda a: temp_atom == a, atomized_list):
            # i.e. if temp_atom is not any atom in atomized_list.
            # This is checked by calling DependsAtom.__eq__().
                #utils.debug.dprint("DependsTree: atomize_depends_list();379 ')'-2, atomized_list.append(temp_atom) = " + str(temp_atom) + ", parent = " +str(parent))
                atomized_list.append(temp_atom)
            temp_atom = None
            depends_list.pop(0)
    #utils.debug.dprint("DependsTree: atomize_depends_list();383 finished recursion level, returning atomized list")
    return atomized_list
    
def split_group(dep_list):
    """separate out the ( ) grouped dependencies"""
    utils.debug.dprint("DependsTree: split_group(); starting")
    group = []
    remainder = []
    if dep_list[0] != '(':
        utils.debug.dprint("DependsTree: split_group();dep_list passed does not start with a '(', returning")
        return group, dep_list
    dep_list.pop(0)
    nest_level = 0
    while dep_list:
        x = dep_list[0]
        #utils.debug.dprint("DependsTree: split_group(); x = " + x)
        if x in '(':
                nest_level += 1
                #utils.debug.dprint("DependsTree: split_group(); nest_level = " + str(nest_level))
        elif x in ')':
            if nest_level == 0:
                dep_list.pop(0)
                break
            else:
                nest_level -= 1
                #utils.debug.dprint("DependsTree: split_group(); nest_level = " + str(nest_level))
        group.append(x)
        dep_list.pop(0)
    #utils.debug.dprint("DependsTree: split_group(); dep_list parsed, group = " + str(group))
    #utils.debug.dprint("DependsTree: split_group(); dep_list parsed, remainder = " + str(dep_list))
    return group, dep_list

def get_depends(package, ebuild):
    if package == None or ebuild == None:
        return ''
    return (package.get_properties(ebuild).depend.split() +
                   package.get_properties(ebuild).rdepend.split() +
                   package.get_properties(ebuild).pdepend.split())
