#!/usr/bin/env python

"""
    PortageLib
    An interface library to Gentoo's Portage

    Copyright (C) 2003 Fredrik Arnerup and Daniel G. Taylor

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

from sys import exit
try:    
    import portage
except ImportError:
    exit('Could not find portage module.\n'
         'Are you sure this is a Gentoo system?')

import threading

version = 0.1
debug = 0

def dprint(message):
    #print debug messages
    if debug:
        print message

def get_name(full_name):
    """Extract name from full name."""
    return full_name.split('/')[1]

def get_category(full_name):
    """Extract category from full name."""
    return full_name.split('/')[0]

def get_version(ebuild):
    """Extract version number from ebuild name"""
    result = ''
    parts = portage.catpkgsplit(ebuild)
    if parts:
        result = parts[2]
        if parts[3] != 'r0':
            result += '-' + parts[3]
    return result

def get_property(ebuild, property):
    """Read a property of an ebuild. Returns a string."""
    # portage.auxdbkeys contains a list of properties
    try:
        return portage.portdb.aux_get(ebuild,
                                      [property])[0]
    except:
        return ''

def get_homepage(ebuild):
    return get_property(ebuild, 'HOMEPAGE')

def get_license(ebuild):
    return get_property(ebuild, 'LICENSE')

def get_slot(ebuild):
    """Return slot number as an integer."""
    try:
        return int(get_property(ebuild, 'SLOT'))
    except ValueError:
        return 0   # ?
        
def get_keywords(ebuild):
    """Returns a list of strings."""
    return get_property(ebuild, 'KEYWORDS').split()

def get_use_flags(ebuild):
    """Returns a list of strings."""
    return get_property(ebuild, 'IUSE').split()

def get_description(ebuild):
    """Returns utf-8 encoded string."""
    return get_property(ebuild, 'DESCRIPTION').encode('UTF-8')

# Todo: dependencies need to be parsed somehow

def get_depend(ebuild):
    return get_property(ebuild, 'DEPEND')

def get_rdepend(ebuild):
    return get_property(ebuild, 'RDEPEND')

class Package:
    """An entry in the package database"""

    def __init__(self, full_name):
        self.full_name = full_name
        self.description = ''
        self.installed = portage.db['/']['vartree'].dep_match(full_name)
        #self.read_description()  # too slow, no dough
        
    def get_name(self):
        return get_name(self.full_name)

    def get_category(self):
        return get_category(self.full_name)

    def get_latest_ebuild(self, include_masked = 1):
        criterion = include_masked and 'match-all' or 'match-visible'
        return portage.best(portage.portdb.xmatch(criterion, self.full_name))

    def get_homepage(self):
        return get_homepage(self.get_latest_ebuild())

    def get_license(self):
        return get_license(self.get_latest_ebuild())

    def get_slot(self):
        return get_slot(self.get_latest_ebuild())

    def get_keywords(self):
        return get_keywords(self.get_latest_ebuild())

    def get_use_flags(self):
        return get_use_flags(self.get_latest_ebuild())

    def get_installed(self):
        """Returns a list of all installed ebuilds."""
        return self.installed

    def read_description(self):
        """Read description and store in object."""
        try:
            latest = self.get_latest_ebuild()
            if not latest:
                raise Exception('No ebuild found.')
            self.description = get_description(latest) 
        except Exception, e:
            self.description = (
                "An error occured when reading the description:\n"
                + str(e))


def sort(list):
    """sort in alphabetic instead of ASCIIbetic order"""
    spam = [(x[0].upper(), x) for x in list]
    spam.sort()
    return [x[1] for x in spam]


class Database:
    def __init__(self):
        # category dictionary with sorted lists of packages
        self.categories = {}
        self.list = []  # all packages in a list sorted by package name
        
    def get_package(self, full_name):
        """Get a Package object based on full name."""
        try:
            category = get_category(full_name)
            name = get_name(full_name)
            if (category in self.categories
                and name in self.categories[category]):
                return self.categories[category][name]
            else:
                return None
        except:
            print "foo"
            return None


class DatabaseReader(threading.Thread):
    """Builds the database in a separate thread."""

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(1)     # quit even if this thread is still running
        self.db = Database()  # the database
        self.done = 0         # false if the thread is still working
        self.count = 0        # number of packages read so far
        self.error = ""       # may contain error message after completion

    def get_db(self):
        """Returns the database that was read."""
        return self.db

    def read_db(self):
        tree = portage.db['/']['porttree']
        try:
            allnodes = tree.getallnodes()
        except OSError, e:
            # I once forgot to give read permissions
            # to an ebuild I created in the portage overlay.
            self.error = str(e)
            return
        for entry in allnodes:
            category, name = entry.split('/')
            if name == 'timestamp.x':  # why does getallnodes()
                continue               # return timestamps?
            self.count += 1
            if not category in self.db.categories:
                self.db.categories[category] = {}
            data = Package(entry)
            self.db.categories[category][name] = data;
            self.db.list.append((name, data))
        self.db.list = sort(self.db.list)

    def run(self):
        """The thread function."""
        self.read_db()
        self.done = 1   # tell main thread that this thread has finished




if __name__ == "__main__":
    # test program
    import time, sys
    db_thread = DatabaseReader(); db_thread.start()
    while not db_thread.done:
        print db_thread.count
        time.sleep(0.1)
    print
    db = db_thread.get_db()
    while 1:
        print; print "Enter full package name:"
        queries = sys.stdin.readline().split()
        for query in queries:
            print; print query
            package = db.get_package(query)
            if not package:
                print "--- unknown ---"
                continue
            print "Homepage:", package.get_homepage()
            package.read_description()
            print "Description:", package.description
            print "License:", package.get_license()
            print "Slot:", package.get_slot()
            print "Keywords:", package.get_keywords()
            print "USE flags:", package.get_use_flags()
            print "Installed:", package.get_installed()
            print "Latest:", get_version(package.get_latest_ebuild())
            print "Latest unmasked:", get_version(package.get_latest_ebuild(0))

