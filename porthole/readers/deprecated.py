#!/usr/bin/env python

'''
    Porthole Reader Class: Upgradable List Reader
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

import os, time
from types import *

from porthole.utils import debug
#from porthole.sterminal import SimpleTerminal
from porthole import backends
portage_lib = backends.portage_lib
from porthole.db.package import Package
from porthole.readers.commonreader import CommonReader

class DeprecatedReader(CommonReader):
    """ Read available upgrades and store them in a tuple """
    def __init__( self, installed ):
        """ Initialize """
        CommonReader.__init__(self)
        self.installed_items = installed
        self.reader_type = "Deprecated"
        # hack for statusbar updates
        self.progress = 2
        self.categories = {"Packages":None, "Ebuilds":None}
        self.pkg_dict = {}
        self.pkg_count = {}
        for key in self.categories:
            self.pkg_dict[key] = {}
            self.pkg_count[key] = 0
        self.count = 0
        self.pkg_dict_total = 0
 
    def run( self ):
        """fill upgrade tree"""
        debug.dprint("READERS: DeprecatedReader; process id = %d *******************" %os.getpid())
        # find deprecated packages
        for cat, packages in self.installed_items:
            #debug.dprint("READERS: DeprecatedReader; cat = " + str(cat))
            for name, package in packages.items():
                #debug.dprint("READERS: DeprecatedReader; name = " + str(name))
                self.count += 1
                if self.cancelled: self.done = True; return
                deprecated = package.deprecated
                if deprecated:
                    debug.dprint("READERS: DeprecatedReader; found deprecated package: " + package.full_name)
                    self.pkg_dict["Packages"][package.full_name] = package
                    self.pkg_count["Packages"] += 1
                else:
                    # check for deprecated ebuilds
                    ebuilds = package.get_installed()
                    for ebuild in ebuilds:
                        overlay = portage_lib.get_overlay(ebuild)
                        if type(overlay) is IntType: # catch obsolete
                            # add the ebuild to Ebuilds list
                            debug.dprint("READERS: DeprecatedReader; found deprecated ebuild: " + ebuild)
                            self.pkg_dict["Ebuilds"][package.full_name] = package
                            self.pkg_count["Ebuilds"] += 1

        debug.dprint("READERS: DeprecatedReader; done checks, totals next")
        self.pkg_dict_total = 0
        for key in self.pkg_count:
            self.pkg_dict_total += self.pkg_count[key]
            if self.pkg_dict[key] == {}:
                pkg = Package(_("None"))
                self.pkg_dict[key][_("None")] = pkg
        # set the thread as finished
        self.done = True
        debug.dprint("READERS: DeprecatedReader; done :)")
        return

