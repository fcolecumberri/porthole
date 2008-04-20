#!/usr/bin/env python

'''
    Porthole Reader Class: Decription Reader

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

import os

from porthole.utils import debug
from porthole.readers.commonreader import CommonReader

class DescriptionReader( CommonReader ):
    """ Read and store package descriptions for searching """
    def __init__( self, packages ):
        """ Initialize """
        CommonReader.__init__(self)
        self.packages = packages

    def run( self ):
        """ Load all descriptions """
        debug.dprint("READERS: DescriptionReader(); process id = %d *****************" %os.getpid())
        self.descriptions = {}
        for name, package in self.packages:
            if self.cancelled: self.done = True; return
            self.descriptions[name] = package.get_description()
            if not self.descriptions[name]:
                debug.dprint("READERS: DescriptionReader(); No description for " + name)
            self.count += 1
        self.done = True
        debug.dprint("READERS: DescriptionReader(); Done")


