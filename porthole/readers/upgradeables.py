#!/usr/bin/env python

'''
    Porthole Reader Class: Upgradable List Reader

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Brian Dolbec, 
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

import os, time, thread, threading
from sys import stderr
from gettext import gettext as _

from porthole.utils import debug
from porthole.sterminal import SimpleTerminal
from porthole import backends
portage_lib = backends.portage_lib
from porthole import db
from porthole.db.package import Package
from porthole.readers.commonreader import CommonReader
from porthole.utils.utils import get_set_name


PRIORITIES = {_("System"): 0, _("Sets"):1, _("World"):2, _("Dependencies"):3}


class UpgradableListReader(CommonReader):
    """ Read available upgrades and store them in a tuple """
    def __init__( self, installed, sets = None ):
        """ Initialize """
        CommonReader.__init__(self)
        self.installed_items = installed
        ##self.upgrade_only = upgradeonly
        self.sets = sets
        self.reader_type = "Upgradable"
        #self.world = []
        # hack for statusbar updates
        self.progress = 1
        # beginnings of multiple listings for packages in priority order
        # lists could be passed into the function and result in the following
        # eg self.categories = ["Tool Chain", _("System"), _("Sets"), _("World"), _("Dependencies")]
        self.cat_order = [_("System"), _("World"), _("Dependencies")]
        self.categories = {_("System"):None, _("World"):"World", _("Dependencies"):"Dependencies"}
        self.pkg_dict = {}
        self.pkg_count = {}
        self.count = 0
        self.pkg_dict_total = 0
        # command lifted fom emwrap and emwrap.sh
        self.system_cmd = "emerge -ep --nocolor --nospinner system | cut -s -f2 -d ']'| cut -f1 -d '[' | sed 's/^[ ]\+//' | sed 's/[ ].*$//'"
        #self.start = self.run
 
    def run( self ):
        """fill upgrade tree"""
        debug.dprint("READERS: UpgradableListReader(); process id = %d *******************" %os.getpid())
        print >>stderr,  "READERS: UpgradableListReader(); threading.enumerate() = ",threading.enumerate()
        print >>stderr, "READERS: UpgradableListReader(); this thread is :", thread.get_ident(), ' current thread ', threading.currentThread()
        self.get_system_list()
        self.get_sets()
        for key in self.cat_order:
            self.pkg_dict[key] = {}
            self.pkg_count[key] = 0
        ##upgradeflag = self.upgrade_only and True or False
        # find upgradable packages
        for cat, packages in self.installed_items:
            for name, package in packages.items():
                self.count += 1
                if self.cancelled: self.done = True; return
                upgradable = package.is_upgradable()
                # if upgradable: # is_upgradable() = 1 for upgrade, -1 for downgrade
                if upgradable == 1 or upgradable == -1:
                    for key in self.cat_order:
                        if package.in_list(self.categories[key]):
                            self.pkg_dict[key][package.full_name] = package
                            self.pkg_count[key] += 1
                            break
        self.pkg_dict_total = 0
        for key in self.pkg_count:
            self.pkg_dict_total += self.pkg_count[key]
            if self.pkg_dict[key] == {}:
                pkg = Package(_("None"))
                self.pkg_dict[key][_("None")] = pkg
                self.pkg_count[key] = 0
        debug.dprint("READERS: UpgradableListReader(); new pkg_dict = " + str(self.pkg_dict))
        debug.dprint("READERS: UpgradableListReader(); new pkg_counts = " + str(self.pkg_count))
        # set the thread as finished
        self.done = True
        return



    def get_system_list( self, emptytree = False ):
        debug.dprint("READERS: UpgradableListReader; getting system package list")
        if emptytree:
            self.terminal = SimpleTerminal(self.system_cmd, need_output=True,  dprint_output='', callback=None)
            self.terminal._run()
            debug.dprint("READERS: UpgradableListReader; waiting for an 'emerge -ep system'...")
            while self.terminal.reader.process_running:
                time.sleep(0.10)
            self.categories[_("System")] = self.make_list(self.terminal.reader.string)
        else:
            self.categories[_("System")] = portage_lib.get_system_pkgs()
        self.progress = 2
        debug.dprint("READERS: UpgradableListReader; new system pkg list %s" %str(self.categories[_("System")]))

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
            self.categories[_("Sets")+"-"+name] = db.userconfigs.get_source_cplist("SETS", key)
            sets_list.append(_("Sets")+"-"+name)
        self.cat_order = [_("System")] + sets_list + [_("World"), _("Dependencies")]
        return #sets_lists
                
