#!/usr/bin/env python

"""
    Package Database
    A database of Gentoo's Portage tree

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor,
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
print "DATABASE: id initialized to ", id

import pwd, cPickle, os
import gobject

from porthole.db.package import Package
from porthole import backends
portage_lib = backends.portage_lib
from porthole.db.dbreader import DatabaseReader
from porthole.readers.descriptions import DescriptionReader
from porthole.db.dbbase import DBBase
from porthole.utils.dispatcher import Dispatcher
from porthole.backends.utilities import get_sync_info
from porthole.utils import debug
from porthole import config


NEW = 0
LOAD = 1
SAVE = 2


class Database(DBBase):
    def __init__(self, action):
        DBBase.__init__(self)
        self.descriptions = {}
        self.desc_loaded = False
        self.desc_reloaded = False
        self.db_thread_running = False
        self.db_init_waiting = False
        self.db_init_new_sync = False
        self.db_thread = None
        self.callback = None
        self.desc_callback = None
        self.desc_thread = None
        ## get home directory
        ##home = pwd.getpwuid(os.getuid())[5]
        self._DBFile = "/var/db/porthole/descriptions.db"
        self.valid_sync = False #used for auto-reload disabling
        ##del home
        #if action == NEW:
        self.db_init()
        #if action == LOAD:
            #result = self.load()
            #if result < 0:
                # create a new db
                #self.db_init()

    def get_package(self, full_name):
        """Get a Package object based on full name."""
        try:
            #debug.dprint("Database: get_package(); fullname = " + full_name)
            category = portage_lib.get_category(full_name)
            name = portage_lib.get_name(full_name)
            if (category in self.categories and name in self.categories[category]):
                return self.categories[category][name]
            else:
                if category != 'virtual':
                    debug.dprint("DATABASE: get_package(); package not found for: " + name + " original full_name = " + full_name)
                    #debug.dprint("DATABASE: get_package(); self.categories[category] = " + str(self.categories[category].keys()))
                return None
        except Exception, e:
            debug.dprint("DATABASE: get_package(); exception occured: " + str(e))
            return None

    def update_package(self, fullname):
        """Update the package info in the full list and the installed list"""
        #category, name = fullname.split("/")
        category = portage_lib.get_category(full_name)
        name = portage_lib.get_name(full_name)
        if (category in self.categories and name in self.categories[category]):
            self.categories[category][name].update_info()
        if (category in self.installed and name in self.installed[category]):
            self.installed[category][name].update_info()

    def save(self):
        """saves the db to a file"""
        if self.valid_sync and self.desc_reloaded:
            sync_time, self.valid_sync = get_sync_info()
            _db = {'sync_date': sync_time, 'descriptions': self.descriptions}
            debug.dprint("DATABASE: save(); Pickling 'db' to file: " + self._DBFile)
            # pickle it baby, yeah!
            cPickle.dump(_db, open(self._DBFile, "w"))
            del _db
        
    def load(self, filename = None):
        """restores the db from a file"""
        debug.dprint("DATABASE: load() loading 'db' from file: " + self._DBFile)
        _db = None
        current, self.valid_sync = get_sync_info()
        if self.valid_sync and os.access(self._DBFile, os.F_OK):
            _db = cPickle.load(open(self._DBFile))
        elif not self.valid_sync:
            debug.dprint("DATABASE: load(); Current portage tree did Not return a valid sync timestamp, not loading descriptions from the saved file" )
            return -1
        else:
            debug.dprint("DATABASE: load(); file does not exist :" + self._DBFile)
            return -1
        if self.valid_sync and _db['sync_date'] != current:
            debug.dprint("DATABASE: load(); 'db' is out of date")
            return -2
        self.descriptions = _db['descriptions']
        self.desc_loaded = True
        self.desc_mtime = os.stat(self._DBFile).st_mtime
        debug.dprint("DATABASE: load(); file is loaded, mtime = " + str(self.desc_mtime))
        del _db
        return 1
        

    def set_callback(self, callback):
        self.callback = callback

    def db_init(self, new_sync = False):
        if self.db_thread_running:
            self.db_thread_cancell()
            # set the init is waiting flag
            self.db_init_waiting = True
            self.db_init_new_sync = new_sync
        else:
            self.db_thread_running = True
            self.db_thread = DatabaseReader(Dispatcher(self.db_update))
            self.db_thread.start()
            self.db_init_new_sync = False
            if new_sync:
                # force a reload
                self.desc_loaded = False
        
    def db_update(self, args):# extra args for dispatcher callback
        """Update the callback to the number of packages read."""
        #debug.dprint("DB: db_update()")
        #args ["nodecount", "allnodes_length","done"]
        if args["done"] == False:
            if self.callback:
                self.callback(args)
        elif self.db_thread.error:
            # todo: display error dialog instead
            self.db_thread.join()
            self.db_thread_running = False
            if self.callback:
                args['db_thread_error'] = self.db_thread.error
                self.callback(args)
            return False  # disconnect from timeout
        elif self.db_thread.cancelled:
            self.db_thread.join()
            self.db_thread_running = False
        else: # args["done"] == True - db_thread is done
            self.db_thread_running = False
            if self.callback:
                self.callback(args)
            debug.dprint("DATABASE: db_update(); db_thread is done...")
            debug.dprint("DATABASE: db_update(); db_thread.join...")
            self.db_thread.join()
            self.db_thread_running = False
            debug.dprint("DATABASE: db_update(); db_thread.join is done...")
            #del self.db  # clean up the old db
            self.db = self.db_thread.get_db()
            self.categories = self.db.categories
            self.list = self.db.list
            self.installed = self.db.installed
            self.installed_count = self.db.installed_count
            self.pkg_count = self.db.pkg_count
            self.installed_pkg_count = self.db.installed_pkg_count
            del self.db  # clean up
            debug.dprint("DATABASE: db_update(); db is updated")
            self.load_descriptions()
        if self.db_init_waiting:
            self.db_init_waiting = False
            self.db_init(self.db_init_new_sync)

    def load_descriptions(self):
        if not self.desc_loaded:
            #try loading from the db file
            result = self.load()
            if result < 0:
                # create a new db
                self.desc_thread = DescriptionReader(self.list)
                self.desc_thread.start()
                gobject.timeout_add(100, self.desc_thread_update)

    def cancell_desc_update(self):
        if self.desc_thread:
            self.desc_thread.please_die()
            self.desc_thread.join()

    def set_desc_callback(self, callback):
        self.desc_callback = callback

    def desc_thread_update(self):
        """ Update status of description loading process """
        if self.desc_callback:
            # gather  the callback data
            args = {}
            args['cancelled'] = self.desc_thread.cancelled
            args['done'] = self.desc_thread.done
            args['count'] = self.desc_thread.count
        if self.desc_thread.done:
            # grab the db
            self.descriptions = self.desc_thread.descriptions
            if not self.desc_thread.cancelled:
                self.desc_loaded = True
                self.desc_reloaded = True
                if self.desc_callback:
                    self.desc_callback(args)
                # kill off the thread
            self.desc_thread.join()
            debug.dprint("DATABASE: desc_thread_update(); save the db")
            self.save()
            return False
        else:
            # print self.desc_thread.count
            if self.desc_callback:
                self.desc_callback(args)
        return True

    def db_thread_cancell(self):
        if self.db_thread_running:
            self.db_thread.please_die()


