#!/usr/bin/env python

'''
    Porthole Depends TreeModel
    Calculates and stores package dependency information

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor,
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

from gettext import gettext as _

from porthole.utils import debug
from porthole import backends
portage_lib = backends.portage_lib
from porthole.backends.utilities import get_reduced_flags, dep_split, get_sync_info
from porthole.db.package import Package
from porthole import db

class DependAtom:
    """Dependency Atom Class.
    Important methods: __repr__(), __eq__(), is_satisfied().
    """
    def __init__(self, atom = '', name='', parent='', mytype='',
        cmp='', slot='', useflag='', req_use=''
        ):
        self.atom = atom
        self.mytype = mytype
        self.children = []
        if parent != '':
            self.parent = [parent]
        else:
            self.parent = []
        self.useflag = useflag
        self.name = name
        self.slot = slot
        self.required_use = req_use
        self.cmp = cmp
        self.complete = False

    def __repr__(self): # called by the "print" function
        """Returns a human-readable string representation of the DependAtom
        (used by the "print" statement)."""
        #debug.dprint("DependAtom: __repr__(); "  + self.get_depname() + self.get_required_use())
        if self.mytype == 'DEP': 
            #debug.dprint("DependAtom: __repr__(); mytype = DEP, "  + \
                #self.get_depname() + self.get_required_use())
            return self.get_depname() + self.get_required_use()
        elif self.mytype == 'BLOCKER': 
            #debug.dprint("DependAtom: __repr__(); mytype = BLOCKER, "  + \
                #self.get_depname() + self.get_required_use())
            return '!' + self.get_depname() + self.get_required_use()
        elif self.mytype == 'OPTION': prefix = '||'
        elif self.mytype == 'GROUP': prefix = ''
        elif self.mytype == 'USING': prefix = self.useflag + '?'
        elif self.mytype == 'NOTUSING': prefix = '!' + self.useflag + '?'
        elif self.mytype == 'REVISIONABLE':
            #debug.dprint("DependAtom: __repr__(); mytype = REVISIONABLE, "  + \
                #self.get_depname() + self._required_use())
            return '~' + self.get_depname() + self.get_required_use()
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
                or self.mytype != test_atom.mytype
                or self.name != test_atom.name
                or self.slot != test_atom.slot
                or self.useflag != test_atom.useflag
                or self.required_use != test_atom.required_use
                or self.children != test_atom.children): # children will recurse
            return False
        else: return True

    def __ne__(self, other):
        return not self == other
        
    def __hash__(self):
        return hash((self.atom, tuple(self.useflag), self.required_use, self.slot))

    def is_satisfied(self, use_flags):
        """Currently returns an object of variable DEPEND type, indicating whether
        this dependency is satisfied.
        
        Returns -1 if being satisfied is irrelevant (e.g. use flag for a
        "USING" DependAtom is not set). Otherwise, the return value can be
        evaluated as True if the dep is satisfied, False if unsatisfied.
        """
        return getattr(self, '_%s_is_satisfied' % self.mytype)(use_flags)
        

    def _DEP_is_satisfied(self, use_flags):
        """ self.mytype == 'DEP
        @rtype: non-empty if satisfied'"""
        return portage_lib.get_installed(self.get_depname() + self.get_required_use())

    def _BLOCKER_is_satisfied(self, use_flags):
        """ self.mytype == 'BLOCKER
        @rtype: non-empty if satisfied????'"""
        return not portage_lib.get_installed(self.get_depname() + self.get_required_use())

    def _GROUP_is_satisfied(self, use_flags):
        """ self.mytype == 'GROUP'
        @rtype: integer
        @rval: 0 if not satisfied, 1 if satisfied"""
        satisfied = 1
        for child in self.children:
            if not child.is_satisfied(use_flags): satisfied = 0
        return satisfied

    def _USING_is_satisfied(self, use_flags):
        """ self.mytype == 'USING' 
        @rtype: integer
        @rval: -1 if not using, 0 if not satisfied, 1 if satisfied"""
        if self.useflag in use_flags:
            satisfied = 1
            for child in self.children:
                if not child.is_satisfied(use_flags): satisfied = 0
        else: satisfied = -1
        return satisfied

    def _NOTUSING_is_satisfied(self, use_flags):
        """ self.mytype == 'NOTUSING' 
        @rtype: integer
        @rval: -1 if using, 0 if not satisfied, 1 if satisfied"""
        if self.useflag not in use_flags:
            satisfied = 1
            for child in self.children:
                if not child.is_satisfied(use_flags): satisfied = 0
        else: satisfied = -1
        return satisfied

    def _REVISIONABLE_is_satisfied(self, use_flags):
        """ self.mytype == 'REVISIONABLE'
        @rtype: nonempty if is satisfied"""
        return portage_lib.get_installed(self.get_depname() + self.get_required_use())

    def _OPTION_is_satisfied(self, use_flags):
        """ self.mytype == 'OPTION' 
        @rtype: nonempty if any child is satisfied"""
        satisfied = []
        for child in self.children:
            a = child.is_satisfied(use_flags)
            if a: satisfied.append(a)
        return satisfied

    def get_depname(self):
        return getattr(self, '_%s_name' % self.mytype)()

    def _USING_name(self):
        """ self.mytype == 'USING'"""
        return _("Using %s") % self.useflag

    def _NOTUSING_name(self):
        """self.mytype == 'NOTUSING'"""
        return _("Not Using %s") % self.useflag

    def _DEP_name(self):
        """ self.mytype =='DEP'"""
        if self.cmp == "=*":
            return "=" + self.name + "*" + self._slot()
        return self.cmp + self.name + self._slot()
        

    def _BLOCKER_name(self):
        """ self.mytype == 'BLOCKER'"""
        return "!" + self._DEP_name()

    def _OPTION_name(self):
        """self.mytype == 'OPTION'"""
        return _("Any of:")

    def _GROUP_name(self):
        """ self.mytype == 'GROUP'"""
        return _("All of:")

    def _REVISIONABLE_name(self):
        """ self.mytype =='REVISIONABLE'"""
        return'~' + self._DEP_name()

    def _slot(self):
        if self.slot != '':
            return ':' + self.slot
        return ''

    def get_required_use(self):
        if self.required_use == '':
            #debug.dprint("DependAtom: get_required_use(); no use")
            return ''
        else:
            #debug.dprint("DependAtom: get_required_use(); required_use = " + self.required_use)
            return "[" + self.required_use +"]"

    def add_parent(self, parent):
        self.parent.append(parent)


class DepCache(object):
    """Dependency cache only applies to final DEP's
    do not store any of [ 'OPTION', 'NOTUSING', 'USING', 'GROUP' ]
    type DepAtoms it will only confuse things"""

    def __init__(self):
        self.reset()
        self.tree_mtime = None
        self.cache = {}

    def get_atom(self, mydep='', mytype='', parent=None):
        try:
            atom = self.cache[mytype+mydep]
            atom.add_parent(parent)
            debug.dprint("DEPENDS: DepCache.get_atom(); Yay! got an existing cache atom: " + \
                mytype + mydep)
        except KeyError:
            name, cmp, slot, use = dep_split(mydep)
            atom = self.cache[mytype+mydep] = DependAtom(atom=mydep, mytype=mytype,
                                                        name=name, parent=parent,
                                                        cmp=cmp, slot=slot,req_use=use)
        return atom

    def reset(self):
        self.tree_mtime, self.valid = get_sync_info()
        self.cache = {}

# create and initialize our DependAtom cache
depcache = DepCache()

def atomize_depends_list(depends_list, parent = None):
    """Takes a list of the form:
    portage.portdb.aux_get(<ebuild>, ["DEPEND"]).split()
    and arranges it into a list of nested list-like DependAtom()s.
    if more closing brackets are encountered than opening ones then it
    will return, meaning we can recursively pass the unparsed part of the
    list back to ourselves...
    """
    global depcache
    atomized_list = []
    temp_atom = None
    while depends_list:
        item = depends_list[0]
        #debug.dprint("DependsTree: atomize_depends_list();321 start of while loop, item = " \
            #+ str(item) + ", parent = " +str(parent))
        if item.startswith("||"):
            temp_atom = DependAtom(mytype='OPTION', parent=parent)
            if item != "||":
                depends_list[0] = item[2:]
                #debug.dprint("DependsTree: atomize_depends_list();327 item != ||, item[2:] = " \
                    #+ str(item[2:]) + ", parent = " +str(parent))
            else:
                depends_list.pop(0)
            item = depends_list[0]
            #debug.dprint("DependsTree: atomize_depends_list();331 new item = " \
                #+ str(item) + ", parent = " +str(parent))
        elif item.endswith("?"):
            temp_atom = DependAtom(parent=parent)
            if item.startswith("!"):
                temp_atom.mytype = 'NOTUSING'
                temp_atom.useflag = item[1:-1]
            else:
                temp_atom.mytype = 'USING'
                temp_atom.useflag = item[:-1]
            depends_list.pop(0)
            item = depends_list[0]
        if item.startswith("("):
            #debug.dprint("DependsTree: atomize_depends_list();343 item.startswith '(', item = " \
                #+ item + ", parent = " +str(parent) + ", temp_atom = " +str(temp_atom))
            if temp_atom is None: # two '(' in a row. Need to create temp_atom
                #debug.dprint("DependsTree: atomize_depends_list();346 item.startswith" + \
                    #'(', new temp_atom for parent: " + str(parent))
                temp_atom = DependAtom(mytype='GROUP',parent=parent)
            if item != "(":
                depends_list[0] = item[1:]
                #debug.dprint("DependsTree: atomize_depends_list();351 item != '(': new depends_list[0]= " + \
                    #str(depends_list[0]))
            else:
                #debug.dprint("DependsTree: atomize_depends_list();353 next " + \
                    #"recursion level, depends_list: " + str(depends_list))
                #debug.dprint("DependsTree: atomize_depends_list();354 next " + \
                    #"recursion level, temp_atom: "+str(temp_atom))
                group, depends_list = split_group(depends_list)
                temp_atom.children = atomize_depends_list(group, temp_atom)
                if not filter(lambda a: temp_atom == a, atomized_list):
                # i.e. if temp_atom is not any atom in atomized_list.
                # This is checked by calling DependAtom.__eq__().
                    #debug.dprint("DependsTree: atomize_depends_list();360 ')'-1, " + \
                        #"atomized_list.append(temp_atom) = " + \
                        #+ str(temp_atom) + ", parent = " +str(parent))
                    atomized_list.append(temp_atom)
                temp_atom = None
                continue
                #debug.dprint("DependsTree: atomize_depends_list();364 item = '(':" + \
                    #" new depends_list[0]= " +str(depends_list[0]))
            #debug.dprint("DependsTree: atomize_depends_list();365 next recursion " + \
                #"level, depends_list: "+str(depends_list))
            #debug.dprint("DependsTree: atomize_depends_list();366 next recursion " + \
                #"level, temp_atom: "+str(temp_atom))
            temp_atom.children = atomize_depends_list(depends_list, temp_atom)
            if not filter(lambda a: temp_atom == a, atomized_list):
                # i.e. if temp_atom is not any atom in atomized_list.
                # This is checked by calling DependAtom.__eq__().
                #debug.dprint("DependsTree: atomize_depends_list();273 ')'-1, atomized_list.append(temp_atom) = " \
                    #+ str(temp_atom) + ", parent = " +str(parent))
                atomized_list.append(temp_atom)
            temp_atom = None
            continue
        elif item.startswith(")"):
            if item != ")":
                depends_list[0] = item[1:]
            else:
                depends_list.pop(0)
                #debug.dprint("DependsTree: atomize_depends_list();283 finished" + \ 
                    #" recursion level, returning atomized list") 
            return atomized_list
        else: # hopefully a nicely formatted dependency
            if filter(lambda a: a in item, ['(', '|', ')']): 
                #  removed '?' from the list due to required USE flags that may have it. 
                debug.dprint(" *** DEPENDS: atomize_depends_list: ILLEGAL ITEM!!! " + \
                    "Please report this to the authorities. (item = %s)" % item)
            if item.startswith("!"):
                #debug.dprint("DependsTree: atomize_depends_list();293 found a BLOCKER dep: " + item)
                item_type = "BLOCKER"
                item = item[1:]
            elif item.startswith('~'):
                #debug.dprint("DependsTree: atomize_depends_list();297 found a " + \
                    #"REVISIONABLE dep: " + item)
                item_type = "REVISIONABLE"
                item = item[1:]
            else:
                #debug.dprint("DependsTree: atomize_depends_list();301 found a DEP dep: " + \
                    #"type=%s, val=%s"  %(type(item),str(item)))
                item_type = "DEP"
            #debug.dprint("DependsTree: atomize_depends_list();303 item type=%s, " + \
                #val='%s'"  %(type(item),str(item)))
            temp_atom = depcache.get_atom(mydep=item, mytype=item_type, parent=parent)

            if not filter(lambda a: temp_atom == a, atomized_list):
                # i.e. if temp_atom is not any atom in atomized_list.
                # This is checked by calling DependsAtom.__eq__().
                #debug.dprint("DependsTree: atomize_depends_list();407 ')'-2," + \
                    #"atomized_list.append(temp_atom) = " + str(temp_atom) + ", parent = " +str(parent))
                atomized_list.append(temp_atom)
            temp_atom = None
            depends_list.pop(0)
    #debug.dprint("DependsTree: atomize_depends_list();411 finished recursion level," + \
        #"returning atomized list")
    return atomized_list
    
def split_group(dep_list):
    """separate out the ( ) grouped dependencies"""
    #debug.dprint("DependsTree: split_group(); starting")
    group = []
    remainder = []
    if dep_list[0] != '(':
        debug.dprint("DependsTree: split_group();dep_list passed does not " + \
            "start with a '(', returning")
        return group, dep_list
    dep_list.pop(0)
    nest_level = 0
    while dep_list:
        x = dep_list[0]
        #debug.dprint("DependsTree: split_group(); x = " + x)
        if x in '(':
                nest_level += 1
                #debug.dprint("DependsTree: split_group(); nest_level = " + str(nest_level))
        elif x in ')':
            if nest_level == 0:
                dep_list.pop(0)
                break
            else:
                nest_level -= 1
                #debug.dprint("DependsTree: split_group(); nest_level = " + str(nest_level))
        group.append(x)
        dep_list.pop(0)
    #debug.dprint("DependsTree: split_group(); dep_list parsed, group = " + str(group))
    #debug.dprint("DependsTree: split_group(); dep_list parsed, remainder = " + str(dep_list))
    return group, dep_list

def get_depends(package, ebuild):
    if package == None or ebuild == None:
        return ''
    return (package.get_properties(ebuild).depend.split() +
                   package.get_properties(ebuild).rdepend.split() +
                   package.get_properties(ebuild).pdepend.split())
