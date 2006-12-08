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
        elif self.type == 'BLOCKER': return ''.join(['!', self.name])
        elif self.type == 'OPTION': prefix = '||'
        elif self.type == 'GROUP': prefix = ''
        elif self.type == 'USING': prefix = ''.join([self.useflag, '?'])
        elif self.type == 'NOTUSING': prefix = ''.join(['!', self.useflag, '?'])
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
            "keyword":7
        }
        self.use_flags = portage_lib.get_portage_environ("USE").split()
        
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
                    

    def add_depends_to_tree(self, depends_list, depends_view, base = None):
        """Add dependencies to the tree"""
        utils.debug.dprint("DependsTree: Parsing depends list")
        depends_list = self.parse_depends_list(depends_list)
        utils.debug.dprint("DependsTree: Finished parsing depends list")
        utils.debug.dprint("DependsTree: depends list = " + str(depends_list))
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
                    utils.debug.dprint("DependsTree; add_depends_to_tree(): Help! Strange parent...")
                if base == None:
                    base_iter = self.insert_before(base, None)
                    self.set_value(base_iter, self.column["depend"], parent)
                    self.set_value(base_iter, self.column["icon"], depends_view.render_icon(parent_icon,
                                        size = gtk.ICON_SIZE_MENU, detail = None))
                    dep_before = base_iter
                last_parent = parent
            elif parent == None:
                dep_before = base
            else:
                dep_before = base_iter
            #self.set_value(depend_iter, self.column["depend"], depend)
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
                        self.set_value(base_iter, self.column["icon"], depends_view.render_icon(gtk.STOCK_NO,
                                       size = gtk.ICON_SIZE_MENU, detail = None))
                        if base != None:
                            base_iter = self.insert_before(base, None)
                            self.set_value(base_iter, self.column["depend"], parent)
                            dep_before = base_iter
                depend_iter = self.insert_before(dep_before, None)
                self.set_value(depend_iter, self.column["depend"], depend)
                self.set_value(depend_iter, self.column["satisfied"], satisfied)
                self.set_value(depend_iter, self.column["icon"], 
                                    depends_view.render_icon(icon,
                                                             size = gtk.ICON_SIZE_MENU,
                                                             detail = None))
                # get depname from depend:
                # The get_text stuff above converted this to unicode, which gives portage headaches.
                # So we have to convert this with str()
                depname = str(portage_lib.get_full_name(depend))
                if not depname: continue
                # pack = Package(depname)
                pack = db.db.get_package(depname)
                self.set_value(depend_iter, self.column["package"], pack)
                if icon != gtk.STOCK_YES:
                    #utils.debug.dprint("Dependency %s not found... recursing..." % str(depname))
                    if depname not in self.depends_list:
                        self.depends_list.append(depname)
                        depends = (pack.get_properties().depend.split() +
                                   pack.get_properties().rdepend.split())
                        if depends:
                            self.add_depends_to_tree(depends, depends_view, depend_iter)
            else:
                #utils.debug.dprint("dependency '%s' skipped" % depend)
                pass

#~ return depend, op
        #~ else:
            #~ return depend, None

    #~ def is_dep_satisfied(self, installed_ebuild, dep_ebuild, operator = "="):
        #~ """ Returns installed_ebuild <operator> dep_ebuild """
        #~ retval = False
        #~ ins_ver = portage_lib.get_version(installed_ebuild)
        #~ dep_ver = portage_lib.get_version(dep_ebuild)
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

    def add_atomized_depends_to_tree(self, atomized_depends_list, depends_view,
                                     parent_iter=None, add_satisfied=1):
        """Add atomized dependencies to the tree"""
        for atom in atomized_depends_list:
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
                elif atom.type == 'DEP':
                    text = atom.name
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
                
                if icon:
                    self.set_value(iter, self.column["icon"], depends_view.render_icon(icon,
                                      size = gtk.ICON_SIZE_MENU, detail = None))
                self.set_value(iter, self.column["depend"], text)
                self.set_value(iter, self.column["satisfied"], bool(satisfied))
                if atom.type in ['DEP', 'BLOCKER']:
                    depname = portage_lib.get_full_name(atom.name)
                    if not depname:
                        utils.debug.dprint(" * DependsTree: add_atomized_depends_list(): No depname found for '%s'" % atom.name or atom.useflag)
                        continue
                    #pack = Package(depname)
                    pack = db.db.get_package(depname)
                    self.set_value(iter, self.column["package"], pack)
                # add kids if we should
                if add_kids and add_satisfied != -1:
                    self.add_atomized_depends_to_tree(atom.children, depends_view, iter, add_kids)

    def fill_depends_tree(self, treeview, package, ebuild):
        """Fill the dependencies tree for a given ebuild"""
        utils.debug.dprint("DependsTree: Updating deps tree for " + package.get_name())
        #ebuild = package.get_default_ebuild()
        ##depends = portage_lib.get_property(ebuild, "DEPEND").split()
        depends = (package.get_properties(ebuild).depend.split() +
                   package.get_properties(ebuild).rdepend.split() +
                   package.get_properties(ebuild).pdepend.split())
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
            utils.debug.dprint("DependsTree: reduced depends = %s" % depends)
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
        utils.debug.dprint("DEPENDS: atomize_depends_list();327 start of while loop, item = " + str(item) + ", parent = " +str(parent))
        if item.startswith("||"):
            temp_atom = DependAtom(parent)
            temp_atom.type = 'OPTION'
            if item != "||":
                depends_list[0] = item[2:]
                utils.debug.dprint("DEPENDS: atomize_depends_list();333 item != ||, item[2:] = " + str(item[2:]) + ", parent = " +str(parent))
            else:
                depends_list.pop(0)
            item = depends_list[0]
            utils.debug.dprint("DEPENDS: atomize_depends_list();337 new item = " + str(item) + ", parent = " +str(parent))
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
            utils.debug.dprint("DEPENDS: atomize_depends_list();349 item.startswith '(', item = " + item + ", parent = " +str(parent) \
                                            + ", temp_atom = " +str(temp_atom))
            if temp_atom is None: # two '(' in a row. Need to create temp_atom
                utils.debug.dprint("DEPENDS: atomize_depends_list();351 item.startswith '(', new temp_atom for parent: " +str(parent))
                temp_atom = DependAtom(parent)
                temp_atom.type = 'GROUP'
            if item != "(":
                depends_list[0] = item[1:]
                utils.debug.dprint("DEPENDS: atomize_depends_list();356 item != '(': new depends_list[0]= " +str(depends_list[0]))
            else:
                utils.debug.dprint("DEPENDS: atomize_depends_list();358 next recursion level, depends_list: "+str(depends_list))
                utils.debug.dprint("DEPENDS: atomize_depends_list();359 next recursion level, temp_atom: "+str(temp_atom))
                group, depends_list = split_group(depends_list)
                temp_atom.children = atomize_depends_list(group, temp_atom)
                if not filter(lambda a: temp_atom == a, atomized_list):
                # i.e. if temp_atom is not any atom in atomized_list.
                # This is checked by calling DependAtom.__eq__().
                    utils.debug.dprint("DEPENDS: atomize_depends_list();365 ')'-1, atomized_list.append(temp_atom) = " + str(temp_atom) + ", parent = " +str(parent))
                    atomized_list.append(temp_atom)
                temp_atom = None
                continue
                utils.debug.dprint("DEPENDS: atomize_depends_list();369 item = '(': new depends_list[0]= " +str(depends_list[0]))
            utils.debug.dprint("DEPENDS: atomize_depends_list();370 next recursion level, depends_list: "+str(depends_list))
            utils.debug.dprint("DEPENDS: atomize_depends_list();371 next recursion level, temp_atom: "+str(temp_atom))
            temp_atom.children = atomize_depends_list(depends_list, temp_atom)
            if not filter(lambda a: temp_atom == a, atomized_list):
            # i.e. if temp_atom is not any atom in atomized_list.
            # This is checked by calling DependAtom.__eq__().
                utils.debug.dprint("DEPENDS: atomize_depends_list();376 ')'-1, atomized_list.append(temp_atom) = " + str(temp_atom) + ", parent = " +str(parent))
                atomized_list.append(temp_atom)
            temp_atom = None
            continue
        elif item.startswith(")"):
            if item != ")":
                depends_list[0] = item[1:]
            else:
                depends_list.pop(0)
                utils.debug.dprint("DEPENDS: atomize_depends_list();385 finished recursion level, returning atomized list") 
            return atomized_list
        else: # hopefully a nicely formatted dependency
            if filter(lambda a: a in item, ['(', '|', ')', '?']):
                utils.debug.dprint(" *** DEPENDS: atomize_depends_list: ILLEGAL ITEM!!! " + \
                    "Please report this to the authorities. (item = %s)" % item)
            temp_atom = DependAtom(parent)
            if item.startswith("!"):
                temp_atom.type = "BLOCKER"
                temp_atom.name = item[1:]
            else:
                temp_atom.type = "DEP"
                temp_atom.name = item
            if not filter(lambda a: temp_atom == a, atomized_list):
            # i.e. if temp_atom is not any atom in atomized_list.
            # This is checked by calling DependsAtom.__eq__().
                utils.debug.dprint("DEPENDS: atomize_depends_list();401 ')'-2, atomized_list.append(temp_atom) = " + str(temp_atom) + ", parent = " +str(parent))
                atomized_list.append(temp_atom)
            temp_atom = None
            depends_list.pop(0)
    utils.debug.dprint("DEPENDS: atomize_depends_list();404 finished recursion level, returning atomized list")
    return atomized_list
    
def split_group(dep_list):
    """separate out the ( ) grouped dependencies"""
    utils.debug.dprint("DEPENDS: split_group(); starting")
    group = []
    remainder = []
    if dep_list[0] != '(':
        utils.debug.dprint("DEPENDS: split_group();dep_list passed does not start with a '(', returning")
        return group, dep_list
    dep_list.pop(0)
    nest_level = 0
    while dep_list:
        x = dep_list[0]
        utils.debug.dprint("DEPENDS: split_group(); x = " + x)
        if x in '(':
                nest_level += 1
                utils.debug.dprint("DEPENDS: split_group(); nest_level = " + str(nest_level))
        elif x in ')':
            if nest_level == 0:
                dep_list.pop(0)
                break
            else:
                nest_level -= 1
                utils.debug.dprint("DEPENDS: split_group(); nest_level = " + str(nest_level))
        group.append(x)
        dep_list.pop(0)
    utils.debug.dprint("DEPENDS: split_group(); dep_list parsed, group = " + str(group))
    utils.debug.dprint("DEPENDS: split_group(); dep_list parsed, remainder = " + str(dep_list))
    return group, dep_list
