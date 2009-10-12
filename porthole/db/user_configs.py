#!/usr/bin/env python

'''
    Porthole user_configs module
    Holds all portage user config data functions for Porthole

    Copyright (C) 2006 - 2009  Brian Dolbec

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

import datetime
id = datetime.datetime.now().microsecond
print "USERCONFIGS: id initialized to ", id

import os

from porthole import config
from porthole.backends.utilities import read_bash, reduce_flags
from porthole.backends import set_config
from porthole.utils.dispatcher import Dispatcher
from porthole.sterminal import SimpleTerminal
from porthole.dialogs.fileselector import FileSelector
from porthole import backends
portage_lib = backends.portage_lib
from porthole.utils import debug

## set up this module to act as a user configs data server,
## watch the user configs for changes and auto update

CONFIG_TYPES = ['USE', 'KEYWORDS', 'MASK', 'UNMASK', 'SETS', 'PROVIDED']
CONFIG_FILES = ['package.use', 'package.keywords', 'package.mask', 'package.unmask', 'sets', 'package.provided']

 # 'all' being a special atom to be replaced with no leading atom and no version info
CONFIG_MASK_ATOMS = ['=',  '<', '>', '<=', '>=', 'all']

def get_type(file):
    if file:
        mytype = set(file.split("/")).intersection(CONFIG_FILES)
        if len(mytype) == 0:
            debug.dprint("USER_CONFIGS: get_type(); failed to determine config type for: " + file)
            return "Uknown"
        else:
            return CONFIG_TYPES[CONFIG_FILES.index(mytype.pop())]

def compare_atoms(a=None, b=None):
    """Function to comare two (ConfigAtom)s and return a value representing the probable match
    name being the most important, followed by version and atoms
    0 = no match
    1 = name only match
    3 = name and version match
    4 = name and atoms match
    5 = name and value match
    6 = name, version and atoms match
    7 = name, version and value match
    10 = considered a full match, as file not used for comaparison
    """
    match = 0
    if a.name == b.name:
        match = 1
        if a.version == b.version:
            match += 2
        if a.atoms == b.atoms:
            match += 3
        if a.value == b.value:
            match +=4
    return match

def cmp(a=None, b=None):
    """comparison function for sorting ConfigAtoms"""
    if a.name == b.name:
        return 0
    if a.name < b.name:
        return -1
    if a.name > b.name:
        return 1
    return 0


class ConfigAtom:
    def __init__(self, name):
        self.name = name                        # pkg name
        self.type = None                         # package.use, package.keywords, etc.
        self.version = ''                          # specific version if defined
        self.atoms = ''                            # any atoms if defined
        self.value = []                              # any keywords, use flags, etc.
        self.file = ''                                 # the file the atom was found in

    def __repr__(self): # called by the "print" function
        """Returns a human-readable string representation of the ConfigAtom
        (used by the "print" statement)."""
        line = self.acpv()
        line = line + ' ' +' '.join(self.value)
        line = line + '  ==> ' + self.file
        return line

    def get_line(self):
        return self.__repr__()

    def acpv(self):
        _acpv = self.atoms +self.name
        if self.version != '':
            _acpv = _acpv + '-'+ self.version
        return _acpv

    def update(self, new):
        self.name = new.name
        self.type = new.type
        self.version = new.version
        self.atoms = new.atoms
        self.value = new.value
        self.file = new.file

class UserConfigs:
    """get and store all user configs data"""
    
    def __init__(self, go):
        debug.dprint("USER_CONFIGS: __init__()")
        # main index files
        self.db = {}
        self.sources = {}
        for mytype in CONFIG_TYPES:
            self.db[mytype] = {}
            self.sources[mytype] = {}
        for file in CONFIG_FILES:
            debug.dprint("USER_CONFIGS: __init__(); file = " + file)
            self.load(os.path.join(portage_lib.settings.config_root, portage_lib.settings.user_config_dir,file))

    def load(self, myfilename, recursive = True):
        lines = []
        debug.dprint("USER_CONFIGS: load(); myfilename = %s, recursive = %s, isdir = %s" %(myfilename, str(recursive), str(os.path.isdir(myfilename))))
        if recursive and os.path.isdir(myfilename):
            dirlist = os.listdir(myfilename)
            dirlist.sort()
            debug.dprint("USER_CONFIGS: load(); dirlist = %s" %str(dirlist))
            for f in dirlist:
                if not f.startswith("."):
                    self.load(os.path.join(myfilename, f), recursive)
        else:
            debug.dprint("USER_CONFIGS: load(); not a directory... so load the file: %s" %myfilename)
            lines = read_bash(myfilename)
            self.atomize(lines, myfilename, self.db, self.sources)

    def atomize(self, lines, source, db = None, sources = None):
        """takes a list of items and creates db records of the package and values"""
        mytype = get_type(source)
        if mytype == None:
            debug.dprint("USER_CONFIGS: atomize(); UNABLE to determine mytype for file: " + str(source))
            debug.dprint("USER_CONFIGS: atomize(); returning without processing file")
            return
        debug.dprint("USER_CONFIGS: atomize(); source = %s, mytype = %s"  %(str(source),str(mytype)))
        for line in lines:
            values = line.split()
            name,atoms, version = portage_lib.split_atom_pkg( values[0] )
            atom = ConfigAtom(name)
            atom.atoms = atoms
            atom.version = version
            atom.file = source
            atom.type = mytype
            atom.value = values[1:]
            #debug.dprint("USER_CONFIGS: atomize(); new atom: " + str(atom.name))
            # index by name
            if name in db[mytype]:
                db[mytype][name].append(atom)
            else:
                db[mytype][name] = [atom]
            # index by source
            if source in sources[mytype]:
                sources[mytype][source].append(atom)
            else:
                sources[mytype][source] = [atom]

    def get_atom(self, mytype, name = None, ebuild = None):
        """searches for a package name and or ebuild version
            and returns the atom or None if not found"""
        result = []
        if mytype not in CONFIG_TYPES:
            return result
        if name and name != '':
            if name in self.db[mytype]:
                result = self.db[mytype][name]
            #~ else:
                #~ result = []
        elif ebuild and ebuild != '':
            #debug.dprint("USER_CONFIGS: get_atom(); ebuild = " + ebuild)
            pkgname = portage_lib.get_full_name(ebuild)
            #debug.dprint("USER_CONFIGS: get_atom(); pkgname = " + pkgname)
            if pkgname in self.db[mytype]:
                result = self.db[mytype][pkgname]
            #~ else:
                #~ result = []
            # match ebuild version
        #debug.dprint("USER_CONFIGS: get_atom(); result = " + str(result))
        return result[:]

    def get_types(self):
        """returns a list of the valid config types"""
        return CONFIG_TYPES

    def get_useflags(self, ebuild):
        """returns a list of the useflags that are configured for the ebuild"""
        atoms = self.get_atom('USE', None, ebuild)
        myflags = []
        for atom in atoms:
            myflags = myflags + atom.value
        myflags = reduce_flags(myflags)
        return myflags

    def get_unmask(self, ebuild):
        pass
        
    def get_keywords(self, ebuild):
        """returns a unique list of matching keywords configured for the ebuild"""
        atoms = self.get_atom('KEYWORDS', None, ebuild)
        keywords = []
        for atom in atoms:
            if atom.atoms != '':
                # check for
                pass
            for x in atom.value:
                if x not in keywords:
                    keywords.append(x)
        return keywords

    def get_user_config(self, mytype, name=None, ebuild=None):
        """
        Function for parsing package.use, package.mask, package.unmask
        and package.keywords.
        
        Returns /etc/portage/<file> as a dictionary of ebuilds, with
        dict[ebuild] = list of flags.
        If name is given, it will be parsed for ebuilds with xmatch('match-all'),
        and only those ebuilds will be returned in dict.
        
        If <ebuild> is given, it will be matched against each line in <file>.
        For package.use/keywords, a list of applicable flags is returned.
        For package.mask/unmask, a list containing the matching lines is returned.
        """
        #debug.dprint("USER_CONFIGS: get_user_config('" + mytype + "')")
        masktypes = ['MASK', 'UNMASK']
        othertypes = ['USE', 'KEYWORDS']
        package_types = othertypes + masktypes
        if mytype not in package_types:
            #debug.dprint("USER_CONFIGS: get_user_config(): unsupported config mytype '%s'" % mytype)
            return None
        atoms = self.get_atom(mytype, name, ebuild)
        dict = {}
        if ebuild is not None:
            result = []
            if atoms == []:
                return result
            for atom in atoms:
                acpv = atom.acpv()
                match = portage_lib.xmatch('match-list', acpv, mylist=[ebuild])
                if match:
                    if mytype in masktypes:
                        result.extend(acpv) # package.mask/unmask
                    else:
                        result.extend(atom.value[:]) # package.use/keywords
            return result
        if name:
            target = portage_lib.xmatch('match-all', name)
            for atom in atoms:
                acpv = atom.acpv()
                ebuilds = portage_lib.xmatch('match-all', acpv)
                for ebuild in ebuilds:
                    if ebuild in target:
                        if ebuild in dict:
                            dict[ebuild].extend(atom.value[:])
                        else:
                            dict[ebuild] = atom.value[:]
        else:
            for atom in atoms:
                acpv = atom.acpv()
                ebuilds = portage_lib.xmatch('match-all', acpv)
                for ebuild in ebuilds:
                    if ebuild in dict:
                        dict[ebuild].extend(atom.value[:])
                    else:
                        dict[ebuild] = atom.value[:]
        return dict

    def set_user_config( self, mytype, name='', ebuild='', add='', remove='', callback=None, parent_window = None, *comment):
        """
        Adds <name> or '=' + <ebuild> to <file> with flags <add>.
        If an existing entry is found, items in <remove> are removed and <add> is added.
        
        If <name> and <ebuild> are not given then lines starting with something in
        remove are removed, and items in <add> are added as new lines.
        """
        #debug.dprint("USER_CONFIGS: set_user_config()")
        self.set_callback = callback
        self.set_type = mytype
        command = ''
        if mytype not in CONFIG_TYPES:
            debug.dprint("USER_CONFIGS: set_user_config(): unsupported config mytype '%s'" % mytype)
            return False
        config_path = os.path.join(portage_lib.settings.config_root, portage_lib.settings.user_config_dir)
        # get an existing atom if one exists.  pass both name and ebuild, no need to check which one, I think
        atom = self.get_atom(mytype, name, ebuild)
        if atom == None or atom == []: # get a target file
            file = target = CONFIG_FILES[CONFIG_TYPES.index(mytype)]
            target_path = os.path.join(config_path, target)
            debug.dprint("USER_CONFIGS: set_user_config(): target_path = " + target_path)
            if os.path.isdir(target_path): # Then bring up a file selector dialog
                if parent_window == None:
                    parent_window = config.Mainwindow
                file_picker = FileSelector(parent_window, os.path.join(target_path, target), overwrite_confirm = False)
                file = file_picker.get_filename(_("Porthole: Please select the %s file to use") \
                                                                %(target))
                file = os.path.join(target_path, file)
            else:
                file = target_path
            debug.dprint("USER_CONFIGS: set_user_config(): got a filename :) file = " + file)

        else: # found one
            file = atom[0].file
            debug.dprint("USER_CONFIGS: set_user_config(): found an atom :) file = " + file)
        self.set_file = file

        if isinstance(add, list):
            add = ' '.join(add)
        if isinstance(remove, list):
            remove = ' '.join(remove)
        if not os.access(config_path, os.W_OK):
            commandlist = [config.Prefs.globals.su, '"python', set_config.__file__ + ' -d -f ' + file]
            if name != '':
                commandlist.append('-n %s' %name)
            if ebuild != '':
                commandlist.append('-e %s' %ebuild)
            comment = '' # for now. TODO add comment input dialog
            commandlist.append('-c %s' %comment)
            if add != '':
                items = add.split()
                for item in items:
                    commandlist.append('-a %s' % item)
            if remove != '':
                items = remove.split()
                for item in items:
                    commandlist.append('-r %s' % item)
            command = ' '.join(commandlist) + '"'
            debug.dprint(" * USER_CONFIGS: set_user_config(): command = %s" %command )
            # add code to update_config()
            mycallback = self.set_config_callback #portage_lib.reload_portage
            app = SimpleTerminal(command, False, dprint_output='SET_USER_CONFIG CHILD APP: ', callback=Dispatcher(mycallback))
            app._run()
        else:
            add = add.split()
            remove = remove.split()
            set_config.set_user_config(file, name, ebuild, comment, add, remove)
            self.set_config_callback()
        return True

    def set_config_callback(self, *args):
        debug.dprint(" * USER_CONFIGS: set_config_callback():" )
        self.reload_file(self.set_type, self.set_file)
        # This is slow, but otherwise portage doesn't notice the change.
        #reload_portage()
        # Note: could perhaps just update portage.settings.
        # portage.settings.pmaskdict, punmaskdict, pkeywordsdict, pusedict
        # or portage.portdb.mysettings ?
        portage_lib.reload_portage()
        if self.set_callback:
            debug.dprint(" * USER_CONFIGS: set_config_callback(): doing self.set_callback()" )
            self.set_callback()


    def reload_file(self, mytype, file):
        """reload a config file due to changes"""
        debug.dprint(" * USER_CONFIGS: reload_file(): mytype = " + mytype + ", file = " + file )
        #return # for now
        # load the file to a temp_db
        temp_db = {}
        temp_sources = {}
        temp_db[mytype] = {}
        temp_sources[mytype] = {}
        lines = []
        lines = read_bash(file)
        if lines:
            self.atomize(lines, file, temp_db, temp_sources)
            temp_sources[mytype][file].sort(cmp)
            new_length = len(temp_sources[mytype][file])
        else:
            new_length = 0
        # get all atoms matching the correct file
        if file in self.sources[mytype]:
            old_file_atoms = self.sources[mytype][file]
            old_file_atoms.sort(cmp)
        else:
            old_file_atoms =  []
        old_length = len(old_file_atoms)
        #debug.dprint(" * USER_CONFIGS: reload_file(): old atoms : " + str(old_file_atoms))
        for a in old_file_atoms:
            # delete the old record
            self.db[mytype][a.name].remove(a)
        if file in self.sources[mytype]:
            del self.sources[mytype][file]
        if new_length == 0:
            return
        # update with the new info
        self.sources[mytype][file] = temp_sources[mytype][file]
        for a in temp_sources[mytype][file]:
            # index by name
            if a.name in self.db[mytype]:
                self.db[mytype][a.name].append(a)
            else:
                self.db[mytype][a.name] = [a]

    def get_source_keys(self, mytype):
        return self.sources[mytype].keys()

    def get_source_atoms(self, mytype, filename):
        return self.sources[mytype][filename]

    def get_source_cplist(self, mytype, key):
        newlist = []
        for atom in self.sources[mytype][key]:
            newlist.append(atom.name)
        return newlist[:]
