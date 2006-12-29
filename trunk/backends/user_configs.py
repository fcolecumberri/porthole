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
from backends.utilities import read_bash

import backends
portage_lib = backends.portage_lib


import utils.debug

## set up this module to act as a user configs data server,
## watch the user configs for changes and auto update

CONFIG_TYPES = ['USE', 'KEYWORD', 'MASK', 'UNMASK', 'SET']
CONFIG_FILES = ['package.use', 'package.keywords', 'package.mask', 'package.unmask', 'sets']

def get_type(file):
    if file:
        parts = file.split('/')
        if parts[-1] not in CONFIG_FILES:
            parts = parts[:-1]
        if parts[-1] not in CONFIG_FILES:
            utils.debug.dprint("USER_CONFIGS: get_typre(); failed to determine config type for: " + file)
        else:
            return CONFIG_TYPES[CONFIG_FILES.index(parts[-1])]

class ConfigAtom:
    def __init__(self, name):
        self.name = name                        # pkg name
        self.type = None                         # package.use, package.keywords, etc.
        self.version = None                      # specific version if defined
        self.atoms = None                      # any atoms if defined
        self.value = []                              # any keywords, use flags, etc.
        self.file = None                           # the file the atom was found in

class UserConfigs:
    """get and store all user configs data"""
    
    def __init__(self):
        self.db = {}
        for type in CONFIG_TYPES:
            self.db[type] = {}
        for file in CONFIG_FILES:
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
            self.atomize(lines, myfilename)

    def atomize(self, lines, source):
        """takes a list of items and creates db records of the package and values"""
        type = get_type(source)
        utils.debug.dprint("USER_CONFIGS: atomize(); type = " + type)
        for line in lines:
            values = line.split()
            name,atoms, version = portage_lib.split_atom_pkg( values[0] )
            atom = ConfigAtom(name)
            atom.atoms = atoms
            atom.file = source
            atom.type = type
            atom.value = values[1:]
            utils.debug.dprint("USER_CONFIGS: atomize(); new atom: " + str(atom.name))
            if name in self.db[type]:
                self.db[type][name].append(atom)
            else:
                self.db[type][name] = [atom]

    def get_atom(self, type, name = None, ebuild = None):
        """searches for a package name and or ebuild version
            and returns the atom or None if not found"""
        if type not in CONFIG_TYPES:
            return None
        result = None
        if name:
            result = self.db[type][name]
        elif ebuild:
            result = self.db[type][portage_lib.get_name(ebuild)]
            # match ebuild version
        return result



