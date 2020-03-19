#!/usr/bin/env python

'''
    Porthole Depends parsing and associated class definitions
    retieves parses and stores package dependency information.

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

from gettext import gettext as _

from porthole.utils import debug
from porthole import backends
portage_lib = backends.portage_lib
from porthole.backends.utilities import get_reduced_flags, dep_split, get_sync_info
#from porthole.utils.enable import Enabler
from porthole.db.package import Package
from porthole import db
import datetime

#from exceptions import Exception


LAZYNAME = "Loading dependencies..."

class DuplicateAtom(Exception):
    """Exception type definition. Duplicate Atom"""
    def __init__(self):
        pass

    def __str__(self):
        return "Group or Option type Atoms are not re-useable"


class DependKey(object):
    """Key generator class to be subclassed. Used for generating unique keys
    for use in hash functions and as dictionary keys"""

    def __init__(self):
        pass

    def get_key(self, mytype, useflag, atom, parent, children):
        """Generates a key based on the mytype parameter
        
        @param mytype:string = one of  ['USING', 'NOTUSING', 'OPTION', 'GROUP',...]
        @param useflag: string  ie.  'ffmpeg'
        @param atom: string  ie. '>=app-portage/porthole-0.6.0'
        @param parent: tuple containing a unigue id
        
        @rtype key: tuple of values
        """
        
        if mytype in ['USING', 'NOTUSING']:
            #debug.dprint("DependKey: ['USING', 'NOTUSING'], mytype = " + mytype)
            return ((mytype, useflag, atom, parent))
        elif mytype in ['OPTION', 'GROUP']:
            #debug.dprint("DependKey: ['OPTION', 'GROUP'], mytype = " + mytype)
            return ((mytype, useflag, atom, parent, tuple(children)))
        elif mytype in ['LAZY']:
            #debug.dprint("DependKey: ['LAZY'], mytype = " + mytype)
            return ((mytype, atom, parent))
        else:  # is a package DependAtom, so type checking is not neccessary
            #debug.dprint("DependKey: Package Dep, mytype = " + mytype)
            return ((mytype, useflag, atom))


class DependAtom(DependKey):
    """Dependency Atom Class.
    Important methods: __repr__(), __eq__(), is_satisfied().
    
        @param atom: string  ie. '>=app-portage/porthole-0.6.0'
        @param name: string  ie. 'app-portage/porthole-0.6.0'
        @param mytpe: string = one of  ['USING', 'NOTUSING', 'OPTION', 'GROUP',...]
        @param parent: tuple containing a unigue id of the parent DependAtom
        @param cmp: string containing any of the comparators from the atom string
        @param slot: string of the package slot
        @param useflag: string  ie.  'ffmpeg'
        @param req_use: string of any required use flag conditionals for package
        @param children: list of child DependAtom keys
    """

    def __init__(self, atom = '', name='', mytype='', parent='',
        cmp='', slot='', useflag='', req_use='', children=None
        ):
        
        self.atom = atom
        self.mytype = mytype
        self.parent = parent
        if children:
            self.children = children
        else:
            self.children = []
        self.useflag = useflag
        self.name = name
        self.slot = slot
        self.required_use = req_use
        self.cmp = cmp
        self.key = None
        self.complete = False

    def __repr__(self): # called by the "print" function
        """Returns a human-readable string representation of the DependAtom
        (used by the "print" statement)."""
        
        if self.mytype == 'DEP': 
            return self.get_depname() + self.get_required_use()
        elif self.mytype == 'BLOCKER': 
            return  self.get_depname() + self.get_required_use()
        elif self.mytype == 'OPTION': prefix = '||'
        elif self.mytype == 'GROUP': prefix = ''
        elif self.mytype == 'USING': prefix = self.useflag + '?'
        elif self.mytype == 'NOTUSING': prefix = '!' + self.useflag + '?'
        elif self.mytype == 'REVISIONABLE':
            return self.get_depname() + self.get_required_use()
        else: return ''
        if self.children:
            bulk = ', '.join([kid.__repr__() for kid in self.children])
            return ''.join([prefix,'[',bulk,']'])
        elif prefix: return ''.join([prefix,'[]'])
        else: return ''

    def __eq__(self, other): # "atomA == atomB" <==> "atomA.__eq__(atomB)"
        """Returns True if the other is equivalent to self
        (used by the statement "atomA == atomB")"""
        if (not isinstance(other, DependAtom)
                or self.mytype != other.mytype
                or self.atom != other.atom
                or self.useflag != other.useflag
                or self.parent != other.parent
                or self.children != other.children): # children will recurse
            return False
        else: return True

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.get_key(self.mytype, self.useflag, self.atom, self.parent, self.children))

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
        @param use_flags: string of space separated use flags
        @rtype: non-empty if satisfied'"""
        return portage_lib.get_installed(self.get_depname() + self.get_required_use())

    def _BLOCKER_is_satisfied(self, use_flags):
        """ self.mytype == 'BLOCKER
        @param use_flags: string of space separated use flags
        @rtype: non-empty if satisfied????'"""
        return not portage_lib.get_installed(self.get_depname() + self.get_required_use())

    def _GROUP_is_satisfied(self, use_flags):
        """ self.mytype == 'GROUP'
        @param use_flags: string of space separated use flags
        @rtype: integer
        @rval: 0 if not satisfied, 1 if satisfied"""
        satisfied = 1
        for child in self.children:
            if not child.is_satisfied(use_flags): satisfied = 0
        return satisfied

    def _USING_is_satisfied(self, use_flags):
        """ self.mytype == 'USING' 
        @param use_flags: string of space separated use flags
        @rtype: integer
        @rval: -1 if not using, 0 if not satisfied, 1 if satisfied"""
        if self.useflag in use_flags:
            satisfied = 1
            for child in self.children:
                if not child.is_satisfied(use_flags):
                    satisfied = 0
                    break
        else: satisfied = -1
        return satisfied

    def _NOTUSING_is_satisfied(self, use_flags):
        """ self.mytype == 'NOTUSING' 
        @param use_flags: string of space separated use flags
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
        @param use_flags: string of space separated use flags
        @rtype: nonempty if is satisfied"""
        return portage_lib.get_installed(self.get_depname() + self.get_required_use())

    def _OPTION_is_satisfied(self, use_flags):
        """ self.mytype == 'OPTION' 
        @param use_flags: string of space separated use flags
        @rtype: nonempty if any child is satisfied"""
        satisfied = []
        for child in self.children:
            a = child.is_satisfied(use_flags)
            if a: satisfied.append(a)
        return satisfied

    def _LAZY_is_satisfied(self, useflags):
        return 0

    def get_depname(self):
        """Returns the dependecy name properly formatted according to 
        the atom's mytype.
        """
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

    def _LAZY_name(self):
        """ self.mytype =='LAZY'"""
        return self.atom


    def _slot(self):
        if self.slot != '':
            return ':' + self.slot
        return ''

    def get_required_use(self):
        """@rtype string of the useflag requirements for the package"""
        if self.required_use == '':
            return ''
        else:
            return "[" + self.required_use +"]"


class DepCache(DependKey):
    """Dependency atom cache and methods/functions for creating, adding,
    and retrieving DependAtom instances and controlling their re-use
    
    Important methods/functions:
        add(), get(), reset()
    """

    def __init__(self):
        #self.tree_mtime = None
        self._cache = {}

    def add(self,  mydep='', mytype='',
                parent='', useflag='', children=None):
        """Add a new DependAtom to the cache if it does not already exist.
        Or returns an existing DependAtom depending on the atom.mytype
        
        @param mytpe: string = one of  ['USING', 'NOTUSING', 'OPTION', 'GROUP',...]
        @param useflag: string  ie.  'ffmpeg'
        @param mydep: string  ie. '>=app-portage/porthole-0.6.0'
        @param parent: tuple containing a unigue id
        @param children: list of child atom keys
        
        @rtype key: a DependKey generated key used to reference the DependAtom instance
        """
        key = self.get_key(mytype, useflag, mydep, parent, children)
        try:
            atom = self._cache[key]
            if atom.mytype in ['USING', 'NOTUSING']:
                #debug.dprint("DepCache: re-using atom" + " %s, %s" % (mytype,useflag))
                if children:
                    #debug.dprint("DepCache: re-using atom, adding more children " +
                    #                        "to %s, %s" % (mytype,useflag))
                    atom.children = list(set(atom.children).union(set(children)))
            elif atom.mytype in ['OPTION', 'GROUP', 'LAZY']:
                # force a new atom.
                #raise DuplicateAtom
                #debug.dprint("DepCache: FORCING a new atom: type=" + mytype )
                self._new(key=key, mydep=mydep, mytype=mytype, useflag=useflag,
                        children=children)
        except KeyError:
            self._new(key=key, mydep=mydep, mytype=mytype, useflag=useflag,
                    children=children)
        #~ except DuplicateAtom:
            #~ self._new(key=key, mydep=mydep, mytype=mytype, useflag=useflag,
                        #~ children=children)
        return key


    def add_lazy(self,  atom):
        """Add a new LAZY DependAtom to the cache.
        
        @param atom: The parent atom instance to be used to link with
        
        @rtype key: a DependKey generated key used to reference the DependAtom instance
        """
        parent = self.get_key(mytype=atom.mytype, useflag=atom.useflag,
                atom=atom.atom, parent=atom.parent, children=atom.children)
        mytype="LAZY"
        useflag= LAZYNAME
        mydep= LAZYNAME
        key = self.get_key(mytype=mytype, useflag=useflag, atom=mydep,
                parent=parent, children=[])
        # move the parents children to the LAZY's Children and make the LAZY atom the
        # child
        self._new(key=key, mydep=mydep, mytype=mytype, useflag=useflag, parent=parent,
                children=[])
        #atom.children = key
        return key

    def _new(self, key, mydep='', mytype='',
                useflag='', parent='', children=None):
        """Creates a new DependAtom instance with supplied
        data and Adds it to the cache. Normally called by the add().
        
        @param key: a DependKey generated key used to reference the DependAtom with 
                    in the cache dict or control atoms set.
        Please refer to the add() for all other input parameter details.
        """
        #debug.dprint("DepCache: new atom: %s, %s, %s " %(mytype, useflag, mydep))
        name, cmp, slot, use = dep_split(mydep)
        atom = DependAtom(atom=mydep, mytype=mytype, useflag=useflag, parent=parent,
                name=name, cmp=cmp, slot=slot,req_use=use, children=children)
        atom.key = key
        self._cache[key] = atom
        return

    def get(self, key):
        """Returns the cached DependAtom associated with 'key'
        
        @param key: DependKey generated key used to refeernce
                    the stored DependAtom
        @rtype atom: The DependAtom instance requested.
        """
        try:
            atom = self._cache[key]
            return atom
        except KeyError:
            return None

    def remove(self, key):
        try:
            self._cache.pop(key)
        except KeyError:
            pass
        return

    def reset(self):
        """Resets the cache to empty.  A must for each
        new package/ebuild to be parsed"""
        #debug.dprint("DEPENDS: DepCache.reset()")
        #self.tree_mtime, self.valid = get_sync_info()
        self._cache = {}


class Depends(object):
    """Depends class for reading and parsing DEPEND atom strings as
    supplied by the package manager for any package and ebuild.
    It will return an organized list of DependAtom instances ready for use
    in a Dependency viewer or any other application the DependAtom model
    is suitable

    Important 
        @variable:flags: a list of USE flags to be filtered out and not parsed.
        @methods/functions: get_depends(), parse()
    """

    def __init__(self):
        # classwide atom cache
        self.cache = DepCache()
        self.flags = []

    def parse(self, depends_list, parent=''):
        """DEPENDS string parsing function. Takes a list of the form:
        portage.portdb.aux_get(<ebuild>, ["DEPEND"]).split()
        and arranges it into a list of nested list-like DependAtom()s.
        if more closing brackets are encountered than opening ones then it
        will return, meaning we can recursively pass the unparsed part of the
        list back to ourselves...
        
        @param depends_list: of the form:
                portage.portdb.aux_get(<ebuild>, ["DEPEND"]).split()
        @param parent: string if a unique parent DependAtom ID that any DependAtoms
                created from this code instance belong to.
        @rtype a nested list of DependAtom instances ready for use.
        """
        atomized_set = set()
        I_am = None
        while depends_list:
            item_type = useflag = ''
            children = []
            a_key = None
            item = depends_list[0]
            if item.startswith("||"):
                item_type = 'OPTION'
                if item != "||":
                    depends_list[0] = item[2:]
                else:
                    depends_list.pop(0)
                item = depends_list[0]
            elif item.endswith("?"):
                if item.startswith("!"):
                    item_type = 'NOTUSING'
                    useflag=item[1:-1]
                else:
                    item_type = 'USING'
                    useflag=item[:-1]
                depends_list.pop(0)
                item = depends_list[0]
            if item.startswith("("):
                if item_type == '': # two '(' in a row. Need to create a new atom?
                    item_type = 'GROUP'
                if item != "(":
                    depends_list[0] = item[1:]
                else:
                    if not I_am:
                        I_am = tuple((parent, datetime.datetime.now()))
                    group, depends_list = self.split_group(depends_list)
                    children = self.parse(group, I_am)
                    a_key = self.cache.add(mytype=item_type, parent=I_am,
                                            useflag=useflag, children=children)
                    atomized_set.add(a_key)
                    a_key = None
                    continue
                if not I_am:
                    I_am = tuple((parent, datetime.datetime.now()))
                children = self.parse(depends_list, I_am)
                a_key = cache.add(mytype=item_type, parent=I_am,
                                        useflag=useflag, children=children)
                atomized_set.add(a_key)
                a_key = None
                continue
            elif item.startswith(")"):
                if item != ")":
                    depends_list[0] = item[1:]
                else:
                    depends_list.pop(0)
                return self._atomized_list(atomized_set)
            else: # hopefully a nicely formatted dependency
                #if filter(lambda a: a in item, ['(', '|', ')']):<== EAPI 3 will kill this [flag1(+), flag2(-)]
                    #  removed '?' from the list due to required USE flags that may have it. 
                    #~ debug.dprint(" *** DEPENDS: atomize_depends_list: DEPENDS PARSE ERROR!!! " + \
                        #~ "Please report this to the authorities. (item = %s)" % item)
                if item.startswith("!"):
                    item_type = "BLOCKER"
                    item = item[1:]
                elif item.startswith('~'):
                    item_type = "REVISIONABLE"
                    item = item[1:]
                else:
                    item_type = "DEP"
                
                a_key = self.cache.add(mydep=item, mytype=item_type)
                atomized_set.add(a_key)
                a_key = None
                depends_list.pop(0)
        #~ debug.dprint("Depends: atomize_depends_list(); finished recursion level," + \
            #~ "returning atomized list")
        return self._atomized_list(atomized_set)

    def _atomized_list(self, a_set):
        """Converts a set of atom keys into a list of DependAtom instances

        @param a_set: set of DependKey keys for conversion
        @rtype a_list: the list of DependAtom instances referenced by the keys
        """
        a_list = []
        while a_set:
            key = a_set.pop()
            atom = self.cache.get(key)
            if atom:
                a_list.append(atom)
        #if a_list:
        #    a_list.reverse()
        return a_list

    def split_group(self, dep_list):
        """Separate out the ( ) grouped dependencies from a dependency list

        @param dep_list: the list of dependencies to split
        @rtype group: list of dependency members contained within the group
        @rtype dep_list: the remainder of the dendency list supplied for splitting
        """
        #debug.dprint("Depends: split_group(); starting")
        group = []
        remainder = []
        if dep_list[0] != '(':
            debug.dprint("Depends: split_group();dep_list passed does not " + \
                "start with a '(', returning")
            return group, dep_list
        dep_list.pop(0)
        nest_level = 0
        while dep_list:
            x = dep_list[0]
            #debug.dprint("Depends: split_group(); x = " + x)
            if x in '(':
                    nest_level += 1
                    #debug.dprint("Depends: split_group(); nest_level = " + str(nest_level))
            elif x in ')':
                if nest_level == 0:
                    dep_list.pop(0)
                    break
                else:
                    nest_level -= 1
                    #debug.dprint("Depends: split_group(); nest_level = " + str(nest_level))
            group.append(x)
            dep_list.pop(0)
        #debug.dprint("Depends: split_group(); dep_list parsed, group = " + str(group))
        #debug.dprint("Depends: split_group(); dep_list parsed, remainder = " + str(dep_list))
        return group, dep_list

    def get_depends(self, package, ebuild):
        """Returns a list of DEPEND atoms for a given package and ebuild
        
        Optionally it will return a list stripped of any predefined flags
        and their dependencies.  ie. Depends.flags = ['!bootstrap!']
        
        @param package: porthole.db.package.Package object
        @param ebuild: specific ebuild version of the 
               package to get the dependency list for
        @rtype deps: a list of depends atom strings
        """
        if package == None or ebuild == None:
            return ''
        props = package.get_properties(ebuild)
        deps = props.depend
        #debug.dprint("Depends: get_depends(); depend=" + deps + "\n")
        if props.rdepend not in deps:
            #debug.dprint("Depends: get_depends(); joining rdepend=" + props.rdepend + "\n")
            deps = ' '.join([deps, props.rdepend])
        if props.pdepend not in deps:
            #debug.dprint("Depends: get_depends(); joining pdepend=" + props.pdepend + "\n")
            deps = ' '.join([deps, props.pdepend])
        deps = deps.split()
        if self.flags:
            deps = self._filter_flags(deps)
        #debug.dprint("Depends: get_depends(); deps = \n"+ str(deps))
        return deps

    def _filter_flags(self, depends):
        """Remove any flag enabled dependency entries from depends list
        
        @param depends: list of DEPEND atom strings
        @rtype depends: list of DEPEND atom strings ready for parsing.
        """
        for flag in self.flags:
            x = 0
            while x < len(depends):
                if depends[x] == flag:
                    depends.pop(x) # remove flag
                    depends.pop(x) # remove (
                    level = 1
                    while level:
                        if depends[x] == "(": level += 1
                        if depends[x] == ")": level -= 1
                        depends.pop(x)
                else: x += 1
        return depends
