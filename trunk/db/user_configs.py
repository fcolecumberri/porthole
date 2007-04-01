#!/usr/bin/env python

'''
    Porthole user_configs module
    Holds all portage user config data functions for Porthole

    Copyright (C) 2006  Brian Dolbec

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

import os

import config
from backends.utilities import read_bash, reduce_flags
from utils.dispatcher import Dispatcher
from sterminal import SimpleTerminal
from dialogs.fileselector import FileSelector
import backends
portage_lib = backends.portage_lib

import utils.debug

## set up this module to act as a user configs data server,
## watch the user configs for changes and auto update

CONFIG_TYPES = ['USE', 'KEYWORDS', 'MASK', 'UNMASK', 'SETS']
CONFIG_FILES = ['package.use', 'package.keywords', 'package.mask', 'package.unmask', 'sets']

def get_type(file):
    if file:
        parts = file.split('/')
        if parts[-1] not in CONFIG_FILES:
            parts = parts[:-1]
        if parts[-1] not in CONFIG_FILES:
            utils.debug.dprint("USER_CONFIGS: get_type(); failed to determine config type for: " + file)
        else:
            return CONFIG_TYPES[CONFIG_FILES.index(parts[-1])]

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
        utils.debug.dprint("USER_CONFIGS: __init__()")
        self.db = {}
        for type in CONFIG_TYPES:
            self.db[type] = {}
        for file in CONFIG_FILES:
            utils.debug.dprint("USER_CONFIGS: __init__(); file = " + file)
            self.load(os.path.join(portage_lib.user_config_dir,file))

    def load(self, myfilename, recursive = True):
        lines = []
        if recursive and os.path.isdir(myfilename):
            dirlist = os.listdir(myfilename)
            dirlist.sort()
            for f in dirlist:
                if not f.startswith("."):
                    self.load(os.path.join(myfilename, f), recursive)
        else:
            lines = read_bash(myfilename)
            self.atomize(lines, myfilename, self.db)

    def atomize(self, lines, source, db = None):
        """takes a list of items and creates db records of the package and values"""
        type = get_type(source)
        utils.debug.dprint("USER_CONFIGS: atomize(); type = " + type)
        for line in lines:
            values = line.split()
            name,atoms, version = portage_lib.split_atom_pkg( values[0] )
            atom = ConfigAtom(name)
            atom.atoms = atoms
            atom.version = version
            atom.file = source
            atom.type = type
            atom.value = values[1:]
            utils.debug.dprint("USER_CONFIGS: atomize(); new atom: " + str(atom.name))
            # index by name
            if name in db[type]:
                db[type][name].append(atom)
            else:
                db[type][name] = [atom]
            # index by source
            if source in db[type]:
                db[type][source].append(atom)
            else:
                db[type][source] = [atom]

    def get_atom(self, type, name = None, ebuild = None):
        """searches for a package name and or ebuild version
            and returns the atom or None if not found"""
        if type not in CONFIG_TYPES:
            return None
        result = None
        if name and name != '':
            if name in self.db[type]:
                result = self.db[type][name]
            else:
                result = []
        elif ebuild and ebuild != '':
            utils.debug.dprint("USER_CONFIGS: get_atom(); ebuild = " + ebuild)
            pkgname = portage_lib.get_full_name(ebuild)
            utils.debug.dprint("USER_CONFIGS: get_atom(); pkgname = " + pkgname)
            if pkgname in self.db[type]:
                result = self.db[type][pkgname]
            else:
                result = []
            # match ebuild version
        utils.debug.dprint("USER_CONFIGS: get_atom(); result = " + str(result))
        return result

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

    def get_user_config(self, type, name=None, ebuild=None):
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
        utils.debug.dprint("USER_CONFIGS: get_user_config('" + type + "')")
        masktypes = ['MASK', 'UNMASK']
        othertypes = ['USE', 'KEYWORDS']
        package_types = othertypes + masktypes
        if type not in package_types:
            utils.debug.dprint("USER_CONFIGS: get_user_config(): unsupported config type '%s'" % type)
            return None
        atoms = self.get_atom(type, name, ebuild)
        dict = {}
        if ebuild is not None:
            result = []
            for atom in atoms:
                acpv = atom.acpv()
                match = portage_lib.xmatch('match-list', acpv, mylist=[ebuild])
                if match:
                    if type in masktypes:
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

    def set_user_config( self, type, name='', ebuild='', add='', remove='', callback=None, parent_window = None):
        """
        Adds <name> or '=' + <ebuild> to <file> with flags <add>.
        If an existing entry is found, items in <remove> are removed and <add> is added.
        
        If <name> and <ebuild> are not given then lines starting with something in
        remove are removed, and items in <add> are added as new lines.
        """
        utils.debug.dprint("USER_CONFIGS: set_user_config()")
        self.set_callback = callback
        self.set_type = type
        command = ''
        if type not in CONFIG_TYPES:
            utils.debug.dprint("USER_CONFIGS: set_user_config(): unsupported config type '%s'" % type)
            return False
        config_path = portage_lib.user_config_dir
        # get an existing atom if one exists.  pass both name and ebuild, no need to check which one, I think
        atom = self.get_atom(type, name, ebuild)
        if atom == None or atom == []: # get a target file
            file = target = CONFIG_FILES[CONFIG_TYPES.index(type)]
            target_path = os.path.join(portage_lib.user_config_dir, target)
            if os.path.isdir(target_path): # Then bring up a file selector dialog
                if parent_window == None:
                    parent_window = config.Mainwindow
                file_picker = FileSelector(parent_window, target_path)
                file = file_picker.get_filename(_("Porthole: Please select the %s file to use") \
                                                                %(target))
                file = os.path.join(target_path, file)
            else:
                file = target_path
            utils.debug.dprint("USER_CONFIGS: set_user_config(): got a filename :) file = " + file)

        else: # found one
            file = atom[0].file
            utils.debug.dprint("USER_CONFIGS: set_user_config(): found an atom :) file = " + file)
        self.set_file = file

        if isinstance(add, list):
            add = ' '.join(add)
        if isinstance(remove, list):
            remove = ' '.join(remove)
        if not os.access(config_path, os.W_OK):
            commandlist = [config.Prefs.globals.su, '"python', config.Prefs.DATA_PATH + 'backends/set_config.py -d -f ' + file]
            if name != '':
                commandlist.append('-n %s' %name)
            if ebuild != '':
                commandlist.append('-e %s' %ebuild)
            if add != '':
                items = add.split()
                for item in items:
                    commandlist.append('-a %s' % item)
            if remove != '':
                items = remove.split()
                for item in items:
                    commandlist.append('-r %s' % item)
            command = ' '.join(commandlist) + '"'
            utils.debug.dprint(" * USER_CONFIGS: set_user_config(): command = %s" %command )
            # add code to update_config()
            mycallback = self.set_config_callback #portage_lib.reload_portage
            app = SimpleTerminal(command, False, dprint_output='SET_USER_CONFIG CHILD APP: ', callback=Dispatcher(mycallback))
            app._run()
        else:
            import backends.set_config
            add = add.split()
            remove = remove.split()
            set_config.set_user_config(file, name, ebuild, add, remove)
            self.set_config_callback()
        return True

    def set_config_callback(self, *args):
        utils.debug.dprint(" * USER_CONFIGS: set_config_callback():" )
        self.reload_file(self.set_type, self.set_file)
        # This is slow, but otherwise portage doesn't notice the change.
        #reload_portage()
        # Note: could perhaps just update portage.settings.
        # portage.settings.pmaskdict, punmaskdict, pkeywordsdict, pusedict
        # or portage.portdb.mysettings ?
        portage_lib.reload_portage()
        if self.set_callback:
            utils.debug.dprint(" * USER_CONFIGS: set_config_callback(): doing self.set_callback()" )
            self.set_callback()


    def reload_file(self, type, file):
        """reload a config file due to changes"""
        utils.debug.dprint(" * USER_CONFIGS: reload_file(): type = " + type + ", file = " + file )
        #return # for now
        # load the file to a temp_db
        temp_db = {}
        temp_db[type] = {}
        lines = []
        lines = read_bash(file)
        self.atomize(lines, file, temp_db)
        # get all atoms matching the correct file
        old_file_atoms = self.db[type][file]
        old_file_atoms.sort(cmp)
        old_length = len(old_file_atoms)
        temp_db[type][file].sort(cmp)
        new_length = len(temp_db[type][file])
        utils.debug.dprint(" * USER_CONFIGS: reload_file(): old atoms : " + str(old_file_atoms))
        for a in old_file_atoms:
            # delete the old record
            self.db[type][a.name].remove(a)
        del self.db[type][file]
        self.db[type][file] = temp_db[type][file]
        for a in temp_db[type][file]:
            # index by name
            if a.name in self.db[type]:
                self.db[type][a.name].append(a)
            else:
                self.db[type][a.name] = [a]

