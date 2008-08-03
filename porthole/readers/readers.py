#!/usr/bin/env python

'''
    Porthole Reader Classes
    The main interface the user will interact with

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


## DEPRICATED MODULE

import threading, re, gtk, os, cPickle, time
from gettext import gettext as _

from views import DependsView, CommonTreeView
import utils.debug
from utils.utils import get_icon_for_package, get_icon_for_upgrade_package
from sterminal import SimpleTerminal
import backends
portage_lib = backends.portage_lib


EXCEPTION_LIST = ['.','^','$','*','+','?','(',')','\\','[',']','|','{','}']

class ToolChain:
    """Class to handle all toolchain related info and decisions"""
    def __init__( self, build ):
        self.build = build
        self.tc_conf = ""
        self.tc_stdc = ""
        self.TC_build = ["sys-kernel/linux-headers", "sys-libs/glibc", tc_conf, \
                      "sys-devel/binutils", "sys-devel/gcc", tc_stdc]
        self.TC="linux-headers glibc $tc_conf_regx binutils-[0-9].* gcc-[0-9].* glibc binutils-[0-9].* gcc-[0-9].* $tc_stdc"
        self.TC_glb="glibc $tc_conf_regx binutils-[0-9].* gcc-[0-9].* glibc binutils-[0-9].* gcc-[0-9].* $tc_stdc"
        self.TCmini="$tc_conf_regx binutils-[0-9].* gcc-[0-9].* binutils-[0-9].* gcc-[0-9].* $tc_stdc"
        self.TC1="linux-headers glibc $tc_conf_regx binutils-[0-9].* gcc-[0-9].* $tc_stdc"
        self.TC_glb1="glibc $tc_conf_regx binutils-[0-9].* gcc-[0-9].* $tc_stdc"
        self.TCmini1="$tc_conf_regx gcc-[0-9].* binutils-[0-9].* $tc_stdc"


class CommonReader(threading.Thread):
    """ Common data reading class that works in a seperate thread """
    def __init__( self ):
        """ Initialize """
        threading.Thread.__init__(self)
        # for keeping status
        self.count = 0
        # we aren't done yet
        self.done = False
        # cancelled will be set when the thread should stop
        self.cancelled = False
        # quit even if thread is still running
        self.setDaemon(1)

    def please_die( self ):
        """ Tell the thread to die """
        self.cancelled = True

class UpgradableListReader(CommonReader):
    """ Read available upgrades and store them in a tuple """
    def __init__( self, installed, upgrade_only, view_prefs ):
        """ Initialize """
        CommonReader.__init__(self)
        self.installed_items = installed
        self.upgrade_only = upgrade_only
        #self.world = []
        self.view_prefs = view_prefs
        # hack for statusbar updates
        self.progress = 1
        # beginnings of multiple listings for packages in priority order
        # lists could be passed into the function and result in the following
        # eg self.categories = ["Tool Chain", "System", "User list", "World", "Dependencies"]
        self.cat_order = ["Tool Chain","System", "User list1", "World", "Dependencies"]
        self.categories = {"Tool Chain": None, "System":None, "World":"World", "User list1":None, "Dependencies":"Dependencies"}
        self.upgradables = {}
        self.pkg_count = {}
        for key in self.categories:
            self.upgradables[key] = {}
            self.pkg_count[key] = 0
        self.count = 0
        # command lifted fom emwrap and emwrap.sh
        self.system_cmd = "emerge -ep --nocolor --nospinner system | cut -s -f2 -d ']'| cut -f1 -d '[' | sed 's/^[ ]\+//' | sed 's/[ ].*$//'"

 
    def run( self ):
        """fill upgrade tree"""
        utils.debug.dprint("READERS: UpgradableListReader(); process id = %d *******************" %os.getpid())
        self.get_system_list()
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
                            self.upgradables[key][package.full_name] = package
                            self.pkg_count[key] += 1
                            break
        self.upgrade_total = 0
        for key in self.pkg_count:
            self.upgrade_total += self.pkg_count[key]
            if self.upgradables[key] == {}:
                pkg = _portage_lib.Package(_("None"))
                self.upgradables[key][_("None")] = pkg
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
            self.categories["System"] = _portage_lib.get_system_pkgs()
        self.progress = 2
        utils.debug.dprint("READERS: UpgradableListReader; new system pkg list %s" %str(self.categories["System"]))

    def make_list(self, from_string):
        """parse terminal output and return a list"""
        list1 = from_string.split('\n')
        list2 = []
        for pkg in list1:
            list2.append(_portage_lib.get_full_name(pkg.rstrip("\r")))
        return list2

    def get_sets( self):
        """Get any package lists stored in the /etc/portage/sets directory
           and add them to the categories list"""
        


class DescriptionReader( CommonReader ):
    """ Read and store package descriptions for searching """
    def __init__( self, packages ):
        """ Initialize """
        CommonReader.__init__(self)
        self.packages = packages

    def run( self ):
        """ Load all descriptions """
        utils.debug.dprint("READERS: DescriptionReader(); process id = %d *****************" %os.getpid())
        self.descriptions = {}
        for name, package in self.packages:
            if self.cancelled: self.done = True; return
            self.descriptions[name] = package.get_properties().description
            if not self.descriptions[name]:
                utils.debug.dprint("READERS: DescriptionReader(); No description for " + name)
            self.count += 1
        self.done = True


class SearchReader( CommonReader ):
    """Create a list of matching packages to searh term"""
    
    def __init__( self, db_list, search_desc, tmp_search_term, desc_db = None, callback = None ):
        """ Initialize """
        CommonReader.__init__(self)
        self.db_list = db_list
        self.search_desc = search_desc
        self.tmp_search_term = tmp_search_term
        self.desc_db = desc_db
        self.callback = callback
        # hack for statusbar updates
        self.progress = 1
        self.package_list = {}
        self.pkg_count = 0
        self.count = 0
    
    
    def run( self ):
            utils.debug.dprint("READERS: SearchReader(); process id = %d *****************" %os.getpid())
            self.search_term = ''
            Plus_exeption_count = 0
            for char in self.tmp_search_term:
                #utils.debug.dprint(char)
                if char in EXCEPTION_LIST:# =="+":
                    utils.debug.dprint("READERS: SearchReader();  '%s' exception found" %char)
                    char = "\\" + char
                self.search_term += char 
            utils.debug.dprint("READERS: SearchReader(); ===> escaped search_term = :%s" %self.search_term)
            re_object = re.compile(self.search_term, re.I)
            # no need to sort self.db_list; it is already sorted
            for name, data in self.db_list:
                if self.cancelled: self.done = True; return
                self.count += 1
                searchstrings = [name]
                if self.search_desc:
                    desc = self.desc_db[name]
                    searchstrings.append(desc)
                if True in map(lambda s: bool(re_object.search(s)),
                               searchstrings):
                    self.pkg_count += 1
                    #package_list[name] = data
                    self.package_list[data.full_name] = data
            utils.debug.dprint("READERS: SearchReader(); found %s entries for search_term: %s" %(self.pkg_count,self.search_term))
            self.do_callback()

    def do_callback(self):
        if self.callback:
            self.done = True
            self.callback()
