#!/usr/bin/env python

"""
    Dbreader, class for reading the portage tree and building a porthole database

    Copyright (C) 2003 - 2009 Fredrik Arnerup, Daniel G. Taylor,
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

import datetime
id = datetime.datetime.now().microsecond
print "DBREADER: import id initialized to ", id

import threading, os

from porthole.utils import debug
from porthole.db.package import Package
from porthole.db.dbbase import DBBase
from porthole import backends
portage_lib = backends.portage_lib

#~ # establish a semaphore for the Database
#~ Installed_Semaphore = threading.Semaphore()

#~ # a list of all installed packages
#~ Installed_Semaphore.acquire()
#~ installed = None
#~ Installed_Semaphore.release()


class DatabaseReader(threading.Thread):
    """Builds the database in a separate thread."""

    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.setDaemon(1)     # quit even if this thread is still running
        self.id = datetime.datetime.now().microsecond
        print "DBREADER: DatabaseReader.id initialized to ", self.id
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
        self.world = portage_lib.settings.get_world()

    def please_die(self):
        """ Tell the thread to die """
        self.cancelled = True

    def get_db(self):
        """Returns the database that was read."""
        return self.db

    def read_db(self):
        """Read portage's database and store it nicely"""
        debug.dprint("DBREADER: read_db(); process id = %d *****************" %(os.getpid()))
        
        self.get_installed()
        try:
            debug.dprint("DBREADER: read_db(); getting allnodes package list")
            allnodes = portage_lib.get_allnodes()
            debug.dprint("DBREADER: read_db(); Done getting allnodes package list")
        except OSError, e:
            # I once forgot to give read permissions
            # to an ebuild I created in the portage overlay.
            self.error = str(e)
            return
        self.allnodes_length = len(allnodes)
        debug.dprint("DBREADER: read_db() create internal porthole list; length=%d" %self.allnodes_length)
        #dsave("db_allnodes_cache", allnodes)
        debug.dprint("DBREADER: read_db(); Threading info: %s" %str(threading.enumerate()) )
        count = 0
        for entry in allnodes:
            if self.cancelled: self.done = True; return
            if count == 250:  # update the statusbar
                self.nodecount += count
                #debug.dprint("DBREADER: read_db(); count = %d" %count)
                self.callback({"nodecount": self.nodecount, "allnodes_length": self.allnodes_length,
                                "done": self.done, 'db_thread_error': self.error})
                count = 0
            count += self.add_pkg(entry)
        # now time to add any remaining installed packages not in the portage tree
        self.db.deprecated_list = self.installed_list[:]
        #debug.dprint("DBREADER: read_db(); deprecated installed packages = " + str(self.db.deprecated_list))
        for entry in self.db.deprecated_list:  # remaining installed packages no longer in the tree
            if self.cancelled: self.done = True; return
            if count == 250:  # update the statusbar
                self.nodecount += count
                #debug.dprint("DBREADER: read_db(); count = %d" %count)
                self.callback({"nodecount": self.nodecount, "allnodes_length": self.allnodes_length,
                                "done": self.done, 'db_thread_error': self.error})
                count = 0
            debug.dprint("DBREADER: read_db(); deprecated entry = " + entry)
            count += self.add_pkg(entry, deprecated=True)

        debug.dprint("DBREADER: read_db(); end of list build; count = %d nodecount = %d" %(count,self.nodecount))
        self.nodecount += count
        debug.dprint("DBREADER: read_db(); end of list build; final nodecount = %d categories = %d sort is next" \
                %(self.nodecount, len(self.db.categories)))
        #debug.dprint(self.db)
        self.db.list = self.sort(self.db.list)
        #debug.dprint(self.db)
        debug.dprint("DBREADER: read_db(); end of sort, finished")

    def add_pkg(self, entry, deprecated = False):
            #debug.dprint("DBREADER: add_pkg(); entry = %s" %entry)
            category, name = entry.split('/')
            if category in ["metadata", "distfiles", "eclass"]:
                return 0
            # why does getallnodes() return timestamps?
            if (name.endswith('tbz2') or \
                    name.startswith('.') or \
                    name in ['timestamp.x', 'metadata.xml', 'CVS'] ):
                return 0
            data = Package(entry)
            data.deprecated = deprecated
            if self.cancelled: self.done = True; return 0
            #self.db.categories.setdefault(category, {})[name] = data;
            # look out for segfaults
            if category not in self.db.categories:
                self.db.categories[category] = {}
                self.db.pkg_count[category] = 0
                #debug.dprint("DBREADER: add_pkg(); added category %s" % str(category))
            self.db.categories[category][name] = data
            if entry in self.installed_list:
                if category not in self.db.installed:
                    self.db.installed[category] = {}
                    self.db.installed_pkg_count[category] = 0
                    #debug.dprint("DBREADER: add_pkg(); added category %s to installed" % str(category))
                self.db.installed[category][name] = data
                self.db.installed_pkg_count[category] += 1
                self.db.installed_count += 1
                #debug.dprint("DBREADER: add_pkg(); adding %s to db.list" %name)
                # remove entry from installed list since it has been added to the db
                self.installed_list.remove(entry)
            self.db.list.append((name, data))
            self.db.pkg_count[category] += 1
            return 1

    def get_installed(self):
        """get a new installed list"""
        debug.dprint("DBREADER: get_installed();")
        self.installed_list = portage_lib.get_installed_list()
        self.installed_count = len(self.installed_list)
        
    def run(self):
        """The thread function."""
        self.read_db()
        self.done = True   # tell main thread that this thread has finished and pass back the db
        self.callback({"nodecount": self.nodecount, "done": True, 'db_thread_error': self.error})
        debug.dprint("DBREADER: DatabaseReader.run(); finished")

    def sort(self, list):
        """sort in alphabetic instead of ASCIIbetic order"""
        debug.dprint("DBREADER: DatabaseReader.sort()")
        spam = [(x[0].upper(), x) for x in list]
        spam.sort()
        debug.dprint("DBREADER: sort(); finished")
        return [x[1] for x in spam]



