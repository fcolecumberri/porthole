#!/usr/bin/env python

'''
    Porthole Reader Class: SearchReader

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

import re, os

from porthole.utils import debug
from porthole.readers.commonreader import CommonReader

EXCEPTION_LIST = ['.','^','$','*','+','?','(',')','\\','[',']','|','{','}']


class SearchReader( CommonReader ):
    """Create a list of matching packages to search term"""
    
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
        self.search_term = ''
    
    
    def run( self ):
            debug.dprint("READERS: SearchReader(); process id = %d *****************" %os.getpid())
            Plus_exeption_count = 0
            for char in self.tmp_search_term:
                #debug.dprint(char)
                if char in EXCEPTION_LIST:# =="+":
                    debug.dprint("READERS: SearchReader();  '%s' exception found" %char)
                    char = "\\" + char
                self.search_term += char 
            debug.dprint("READERS: SearchReader(); ===> escaped search_term = :%s" %self.search_term)
            re_object = re.compile(self.search_term, re.I)
            # no need to sort self.db_list; it is already sorted
            for name, data in self.db_list:
                if self.cancelled: self.done = True; return
                self.count += 1
                searchstrings = [name]
                if self.search_desc:
                    try:
                        desc = self.desc_db[name]
                    except KeyError: # perhaps the description db is stale?
                        desc = ''
                    searchstrings.append(desc)
                    #debug.dprint("searchstrings type = " + str(type(searchstrings)))
                    #debug.dprint(searchstrings)
                if True in map(lambda s: bool(re_object.search(s)), searchstrings):
                    self.pkg_count += 1
                    #package_list[name] = data
                    self.package_list[data.full_name] = data
            debug.dprint("READERS: SearchReader(); found %s entries for search_term: %s" %(self.pkg_count,self.search_term))
            self.do_callback()

    def do_callback(self):
        if self.callback:
            self.done = True
            self.callback()
