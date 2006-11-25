#!/usr/bin/env python

"""
    Dbreader, class for reading the portage tree and building a porthole database

    Copyright (C) 2003 - 2006 Fredrik Arnerup, Daniel G. Taylor,
    Wm. F. Wheeler, Brian Dolbec, Tommy Iorns

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
"""

import threading, os

import utils.debug
from package import Package
from dbbase import DBBase
import backends
portage_lib = backends.portage_lib

# establish a semaphore for the Database
Installed_Semaphore = threading.Semaphore()

# a list of all installed packages
Installed_Semaphore.acquire()
installed = None
Installed_Semaphore.release()


class DatabaseReader(threading.Thread):
    """Builds the database in a separate thread."""

    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.setDaemon(1)     # quit even if this thread is still running
        self.db = DBBase()        # the database
        self.callback = callback
        self.done = False     # false if the thread is still working
        #self.count = 0        # number of packages read so far
        self.nodecount = 0    # number of nodes read so far
        self.error = ""       # may contain error message after completion
        # we aren't done yet
        self.done = False
        # cancelled will be set when the thread should stop
        self.cancelled = False
        #self.new_installed_Semaphore = threading.Semaphore()
        self.installed_list = None
        self.allnodes_length = 0  # used for calculating the progress bar
        self.world = portage_lib.get_world()

    def please_die(self):
        """ Tell the thread to die """
        self.cancelled = True

    def get_db(self):
        """Returns the database that was read."""
        return self.db

    def read_db(self):
        """Read portage's database and store it nicely"""
        utils.debug.dprint("DBREADER: read_db(); process id = %d *****************" %(os.getpid()))
        
        self.get_installed()
        try:
            utils.debug.dprint("DBREADER: read_db(); getting allnodes package list")
            allnodes = portage_lib.get_allnodes()
            utils.debug.dprint("DBREADER: read_db(); Done getting allnodes package list")
        except OSError, e:
            # I once forgot to give read permissions
            # to an ebuild I created in the portage overlay.
            self.error = str(e)
            return
        self.allnodes_length = len(allnodes)
        utils.debug.dprint("DBREADER: read_db() create internal porthole list; length=%d" %self.allnodes_length)
        #dsave("db_allnodes_cache", allnodes)
        utils.debug.dprint("DBREADER: read_db(); Threading info: %s" %str(threading.enumerate()) )
        count = 0
        for entry in allnodes:
            if self.cancelled: self.done = True; return
            if count == 250:  # update the statusbar
                self.nodecount += count
                #utils.debug.dprint("DBREADER: read_db(); count = %d" %count)
                self.callback({"nodecount": self.nodecount, "allnodes_length": self.allnodes_length,
                                "done": self.done, 'db_thread_error': self.error})
                count = 0
            #utils.debug.dprint("DBREADER: entry = %s" %entry)
            category, name = entry.split('/')
            if category in ["metadata", "distfiles", "eclass"]:
                continue
            # why does getallnodes() return timestamps?
            if (name.endswith('tbz2') or \
                    name.startswith('.') or \
                    name in ['timestamp.x', 'metadata.xml', 'CVS'] ):
                continue
            count += 1
            data = Package(entry)
            if self.cancelled: self.done = True; return
            #self.db.categories.setdefault(category, {})[name] = data;
            # look out for segfaults
            if category not in self.db.categories:
                self.db.categories[category] = {}
                self.db.pkg_count[category] = 0
                #utils.debug.dprint("added category %s" % str(category))
            self.db.categories[category][name] = data;
            if entry in self.installed_list:
                if category not in self.db.installed:
                    self.db.installed[category] = {}
                    self.db.installed_pkg_count[category] = 0
                    #utils.debug.dprint("added category %s to installed" % str(category))
                self.db.installed[category][name] = data
                self.db.installed_pkg_count[category] += 1
                self.db.installed_count += 1
                #utils.debug.dprint("DBREADER: read_db(); adding %s to db.list" %name)
            self.db.list.append((name, data))
            self.db.pkg_count[category] += 1
        utils.debug.dprint("PKGCORE_LIB: read_db(); end of list build; count = %d nodecount = %d" %(count,self.nodecount))
        self.nodecount += count
        utils.debug.dprint("PKGCORE_LIB: read_db(); end of list build; final nodecount = %d categories = %d sort is next" \
                %(self.nodecount, len(self.db.categories)))
        #utils.debug.dprint(self.db)
        self.db.list = self.sort(self.db.list)
        #utils.debug.dprint(self.db)
        utils.debug.dprint("DBREADER: read_db(); end of sort, finished")

    def get_installed(self):
        """get a new installed list"""
        # I believe this next variable may be the cause of our segfaults
        # so I' am semaphoring it.  Brian 2004/08/19
        #self.new_installed_Semaphore.acquire()
        #installed_list # a better way to do this?
        utils.debug.dprint("DBREADER: get_installed();")
        self.installed_list = portage_lib.get_installed_list()
        self.installed_count = len(self.installed_list)
        global Installed_Semaphore
        global installed
        Installed_Semaphore.acquire()
        installed = self.installed_list
        Installed_Semaphore.release()
        #self.new_installed_Semaphore.release()
        
    def run(self):
        """The thread function."""
        self.read_db()
        self.done = True   # tell main thread that this thread has finished and pass back the db
        self.callback({"nodecount": self.nodecount, "done": True, 'db_thread_error': self.error})
        utils.debug.dprint("DBREADER: DatabaseReader.run(); finished")

    def sort(self, list):
        """sort in alphabetic instead of ASCIIbetic order"""
        utils.debug.dprint("DBREADER: DatabaseReader.sort()")
        spam = [(x[0].upper(), x) for x in list]
        spam.sort()
        utils.debug.dprint("DBREADER: sort(); finished")
        return [x[1] for x in spam]



