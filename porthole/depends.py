#!/usr/bin/env python

'''
    Porthole Depends TreeModel
    Calculates and stores package dependency information

    Copyright (C) 2003 - 2005 Fredrik Arnerup, Daniel G. Taylor,
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

import gtk, gobject, portagelib, string
from utils import dprint
from gettext import gettext as _

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
        if self.type == 'DEP': return portagelib.get_installed(self.name)
        elif self.type == 'BLOCKER': return not portagelib.get_installed(self.name)
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
                    dprint("DEPENDS; add_depends_to_tree(): Help! Strange parent...")
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
                #dprint("DEPENDS: atom '%s', type '%s', satisfied '%s'" % (atom.name, atom.type, satisfied))
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
                    self.set_value(iter, 1, depends_view.render_icon(icon,
                                      size = gtk.ICON_SIZE_MENU, detail = None))
                self.set_value(iter, 0, text)
                self.set_value(iter, 3, bool(satisfied))
                if atom.type in ['DEP', 'BLOCKER']:
                    depname = portagelib.get_full_name(atom.name)
                    if not depname:
                        dprint(" * DEPENDS: add_atomized_depends_list(): No depname found for '%s'" % atom.name or atom.useflag)
                        continue
                    pack = portagelib.Package(depname)
                    self.set_value(iter, 2, pack)
                # add kids if we should
                if add_kids and add_satisfied != -1:
                    self.add_atomized_depends_to_tree(atom.children, depends_view, iter, add_kids)

    
    def atomize_depends_list(self, depends_list = [], parent = None):
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
            if item.startswith("||"):
                temp_atom = DependAtom(parent)
                temp_atom.type = 'OPTION'
                if item != "||":
                    depends_list[0] = item[2:]
                else:
                    depends_list.pop(0)
                item = depends_list[0]
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
                if temp_atom is None: # two '(' in a row. Need to create temp_atom
                    temp_atom = DependAtom(parent)
                    temp_atom.type = 'GROUP'
                if item != "(":
                    depends_list[0] = item[1:]
                else:
                    depends_list.pop(0)
                temp_atom.children = self.atomize_depends_list(depends_list, temp_atom)
                if not filter(lambda a: temp_atom == a, atomized_list):
                # i.e. if temp_atom is not any atom in atomized_list.
                # This is checked by calling DependAtom.__eq__().
                    atomized_list.append(temp_atom)
                temp_atom = None
                continue
            elif item.startswith(")"):
                if item != ")":
                    depends_list[0] = item[1:]
                else:
                    depends_list.pop(0)
                return atomized_list
            else: # hopefully a nicely formatted dependency
                if filter(lambda a: a in item, ['(', '|', ')', '?']):
                    dprint(" *** DEPENDS: atomize_depends_list: ILLEGAL ITEM!!! " + \
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
                    atomized_list.append(temp_atom)
                depends_list.pop(0)
        return atomized_list
    
    def fill_depends_tree(self, treeview, package):
        """Fill the dependencies tree for a given ebuild"""
        #dprint("DEPENDS: Updating deps tree for " + package.get_name())
        ebuild = package.get_default_ebuild()
        ##depends = portagelib.get_property(ebuild, "DEPEND").split()
        depends = (package.get_properties().depend.split() +
                   package.get_properties().rdepend.split())
        self.clear()
        if depends:
            #dprint("DEPENDS: depends = %s" % depends)
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
            #dprint("DEPENDS: reduced depends = %s" % depends)
            self.depends_list = []
            #self.add_depends_to_tree(depends, treeview)
            atomized_depends = self.atomize_depends_list(depends)
            #dprint(atomized_depends)
            self.add_atomized_depends_to_tree(atomized_depends, treeview)
        else:
            parent_iter = self.insert_before(None, None)
            self.set_value(parent_iter, 0, _("None"))
        treeview.set_model(self)
