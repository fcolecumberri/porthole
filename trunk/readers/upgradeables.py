#!/usr/bin/env python

'''
    Porthole Reader Class: Upgradable List Reader

    Copyright (C) 2003 - 2007 Fredrik Arnerup, Brian Dolbec, 
    Daniel G. Taylor and Wm. F. Wheeler, Tommy Iorns

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

import os, time
import utils.debug
from sterminal import SimpleTerminal

import backends
portage_lib = backends.portage_lib

import db
from db.package import Package
from commonreader import CommonReader
from utils.utils import get_set_name


PRIORTIES = {"System": 0, "Sets":1, "World":2, "Dependencies":3}


class UpgradableListReader(CommonReader):
    """ Read available upgrades and store them in a tuple """
    def __init__( self, installed, upgrade_only, sets = None ):
        """ Initialize """
        CommonReader.__init__(self)
        self.installed_items = installed
        self.upgrade_only = upgrade_only
        self.sets = sets
        self.reader_type = "Upgradable"
        #self.world = []
        # hack for statusbar updates
        self.progress = 1
        # beginnings of multiple listings for packages in priority order
        # lists could be passed into the function and result in the following
        # eg self.categories = ["Tool Chain", "System", "Sets", "World", "Dependencies"]
        self.cat_order = ["System", "World", "Dependencies"]
        self.categories = {"System":None, "World":"World", "Dependencies":"Dependencies"}
        self.pkg_dict = {}
        self.pkg_count = {}
        self.count = 0
        self.pkg_dict_total = 0
        # command lifted fom emwrap and emwrap.sh
        self.system_cmd = "emerge -ep --nocolor --nospinner system | cut -s -f2 -d ']'| cut -f1 -d '[' | sed 's/^[ ]\+//' | sed 's/[ ].*$//'"

 
    def run( self ):
        """fill upgrade tree"""
        utils.debug.dprint("READERS: UpgradableListReader(); process id = %d *******************" %os.getpid())
        self.get_system_list()
        self.get_sets()
        for key in self.cat_order:
            self.pkg_dict[key] = {}
            self.pkg_count[key] = 0
        upgradeflag = self.upgrade_only and True or False
        # find upgradable packages
        for cat, packages in self.installed_items:
            for name, package in packages.items():
                self.count += 1
                if self.cancelled: self.done = True; return
                upgradable = package.is_upgradable()
                # if upgradable: # is_upgradable() = 1 for upgrade, -1 for downgrade
                if upgradable == 1 or (not self.upgrade_only and upgradable == -1):
                    for key in self.cat_order:
                        if package.in_list(self.categories[key]):
                            self.pkg_dict[key][package.full_name] = package
                            self.pkg_count[key] += 1
                            break
        self.pkg_dict_total = 0
        for key in self.pkg_count:
            self.pkg_dict_total += self.pkg_count[key]
            if self.pkg_dict[key] == {}:
                pkg = Package("None")
                self.pkg_dict[key]["None"] = pkg
        #utils.debug.dprint("READERS: UpgradableListReader(); new pkg_list = " + str(self.pkg_dict))
        # set the thread as finished
        self.done = True
        return



    def get_system_list( self, emptytree = False ):
        utils.debug.dprint("READERS: UpgradableListReader; getting system package list")
        if emptytree:
            self.terminal = SimpleTerminal(self.system_cmd, need_output=True,  dprint_output='', callback=None)
            self.terminal._run()
            utils.debug.dprint("READERS: UpgradableListReader; waiting for an 'emerge -ep system'...")
            while self.terminal.reader.process_running:
                time.sleep(0.10)
            self.categories["System"] = self.make_list(self.terminal.reader.string)
        else:
            self.categories["System"] = portage_lib.get_system_pkgs()
        self.progress = 2
        utils.debug.dprint("READERS: UpgradableListReader; new system pkg list %s" %str(self.categories["System"]))

    def make_list(self, from_string):
        """parse terminal output and return a list"""
        list1 = from_string.split('\n')
        list2 = []
        for pkg in list1:
            list2.append(portage_lib.get_full_name(pkg.rstrip("\r")))
        return list2

    def get_sets( self):
        """Get any package lists stored in the /etc/portage/sets directory
           and add them to the categories list"""
        sets_list = []
        for key in db.userconfigs.get_source_keys("SETS"):
            name = get_set_name(key)
            self.categories["Sets-"+name] = db.userconfigs.get_source_cplist("SETS", key)
            sets_list.append("Sets-"+name)
        self.cat_order = ["System"] + sets_list + ["World", "Dependencies"]
        return #sets_lists
                
