#!/usr/bin/env python

'''
    Porthole Reader Class: Sets List Reader

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
import os, types

from porthole.utils import debug
from porthole import backends
portage_lib = backends.portage_lib
from porthole import db
from porthole.db.package import Package
from porthole.readers.commonreader import CommonReader
from porthole.utils.utils import get_set_name

class SetListReader(CommonReader):
    """ Convert userconfigs sets to a filename (category) & pkg (package) db (tuple) """
    def __init__( self ):
        """ Initialize """
        CommonReader.__init__(self)
        self.reader_type = "Sets"
        # hack for statusbar updates
        self.progress = 2
        self.pkg_dict = {}
        self.pkg_count = {}
        self.count = 0
        self.pkg_dict_total = 0

 
    def run( self ):
        """fill SETS tree"""
        debug.dprint("READERS: SetListReader(); process id = %d *******************" %os.getpid())
        debug.dprint("READERS: SetListReader(); db.userconfigs is type : " +str(type(db.userconfigs)))
        filenames = db.userconfigs.get_source_keys("SETS")
        debug.dprint("READERS: SetListReader(); filenames are: " + str(filenames))
        for filename in filenames:
            debug.dprint("READERS: SetListReader(); filename is: " + filename)
            key =get_set_name(filename)
            if key not in self.pkg_dict.keys():
                self.pkg_dict[key] = {}
                self.pkg_count[key] = 0

            for atom in db.userconfigs.get_source_atoms('SETS', filename):
                debug.dprint("READERS: SetListReader(); atom.name is: " + atom.name)
                self.count += 1
                if self.cancelled: self.done = True; return
                self.pkg_dict[key][atom.name] = db.db.get_package(atom.name)
                if self.pkg_dict[key][atom.name] == None:
                    self.pkg_dict[key][atom.name] = Package(atom.name)
                self.pkg_count[key] += 1

        self.pkg_dict_total = 0
        for key in self.pkg_count:
            self.pkg_dict_total += self.pkg_count[key]
            if self.pkg_dict[key] == {}:
                pkg = Package(_("None"))
                self.pkg_dict[key][_("None")] = pkg
        #debug.dprint("READERS: SetListReader(); new pkg_list = " + str(self.pkg_dict))
        # set the thread as finished
        self.done = True
        return


      
