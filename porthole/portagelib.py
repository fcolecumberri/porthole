#!/usr/bin/env python

"""
    PortageLib
    An interface library to Gentoo's Portage

    Copyright (C) 2003 - 2004 Fredrik Arnerup and Daniel G. Taylor and
    Wm. F. Wheeler

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

from utils import dprint, dsave
from sys import exit
import string
from string import digits, zfill
from gettext import gettext as _

try:
    import portage
except ImportError:
    exit(_('Could not find portage module.\n'
         'Are you sure this is a Gentoo system?'))

import threading

# not sure if segfaults are gtk.threads_enter() / _leave() related
# so...
import gtk

from metadata import parse_metadata

def reload_portage():
	reload(portage)
	
def get_keywords():
    """ Get the official keywords as a list """
    return portage.grabfile('/usr/portage/profiles/keywords.desc')

# Get just once for sake of efficiency
KeywordList = get_keywords()
# debug code follows WFW
# print 'Keyword list:', KeywordList

def get_use_flag_dict():
    """ Get all the use flags and return them as a dictionary 
        key = use flag forced to lowercase
        data = list[0] = 'local' or 'global'
               list[1] = 'package-name'
               list[2] = description of flag   
    """
    dict = {}

    # process standard use flags

    List = portage.grabfile('/usr/portage/profiles/use.desc')
    for item in List:
        index = item.find(' - ')
        dict[item[:index].strip().lower()] = ['global', '', item[index+3:]]

    # process local (package specific) use flags

    List = portage.grabfile('/usr/portage/profiles/use.local.desc')
    for item in List:
        index = item.find(' - ')
        data = item[:index].lower().split(':')
        try: # got this error starting porthole==> added code to catch it, but it works again???
##            big_squirt porthole # ./porthole -l -d
##
##            ** (porthole:23062): WARNING **: `GtkTextSearchFlags' is not an enum type
##            Traceback (most recent call last):
##              File "./porthole", line 45, in ?
##                from mainwindow import MainWindow
##              File "/home/brian/porthole/mainwindow.py", line 28, in ?
##                import portagelib, os, string
##              File "/home/brian/porthole/portagelib.py", line 73, in ?
##                UseFlagDict = get_use_flag_dict()
##              File "/home/brian/porthole/portagelib.py", line 69, in get_use_flag_dict
##                dict[data[1].strip()] = ['local', data[0].strip(), item[index+3:]]
##            IndexError: list index out of range
##            big_squirt porthole # ./porthole -l -d
##
            dict[data[1].strip()] = ['local', data[0].strip(), item[index+3:]]
        except:
            dprint("PORTAGELIB: get_use_flag_dict(); error in index??? daata[0].strip, item[index:]")
            dprint(data[0].strip())
            dprint(item[index:])
    return dict

# Run it once for sake of efficiency
UseFlagDict = get_use_flag_dict()
# debug code follows WFW
#polibkeys = UseFlagDict.keys()
#polibkeys.sort()
#for polibkey in polibkeys:
#    print polibkey, ':', UseFlagDict[polibkey]
    
def get_portage_environ(var):
    """Returns environment variable from portage if possible, else None"""
    try: temp = portage.config(clone=portage.settings).environ()[var]
    except: temp = None
    return temp

portdir = portage.config(clone=portage.settings).environ()['PORTDIR']
# is PORTDIR_OVERLAY always defined?
portdir_overlay = get_portage_environ('PORTDIR_OVERLAY')

# Run it once for sake of efficiency
SystemUseFlags = get_portage_environ("USE").split()

# did not work.  need to reload portage
def reset_use_flags():
    dprint("PORTAGELIB: reset_use_flags();")
    global SystemUseFlags
    SystemUseFlags = get_portage_environ("USE").split()



# lower case is nicer
keys = [key.lower() for key in portage.auxdbkeys]

# establish a semaphore for the Database
Installed_Semaphore = threading.Semaphore()

# a list of all installed packages
Installed_Semaphore.acquire()
installed = None
Installed_Semaphore.release()


def get_name(full_name):
    """Extract name from full name."""
    return full_name.split('/')[1]

def get_category(full_name):
    """Extract category from full name."""
    return full_name.split('/')[0]

def get_installed(full_name):
    """Extract installed versions from full name."""
    return portage.db['/']['vartree'].dep_match(full_name)

def get_version(ebuild):
    """Extract version number from ebuild name"""
    result = ''
    parts = portage.catpkgsplit(ebuild)
    if parts:
        result = parts[2]
        if parts[3] != 'r0':
            result += '-' + parts[3]
    return result

def extract_package(ebuild):
    """Returns cat/package from cat/package-ebuild,
       or None if input is not in that format.  """
    result = None
    parts = portage.catpkgsplit(ebuild)
    if parts:
        result = "/".join(parts[0:2])
    return result

def get_installed_files(ebuild):
    """Get a list of installed files for an ebuild, assuming it has
    been installed."""
    path = "/var/db/pkg/" + ebuild + "/CONTENTS"
    files = []
    try:
        # hoping some clown won't use spaces in filenames ...
        files = [line.split()[1].decode('ascii')
                 for line in open(path, "r").readlines()]
    except: pass
    files.sort()
    return files

# this is obsolete
def get_property(ebuild, property):
    """Read a property of an ebuild. Returns a string."""
    # portage.auxdbkeys contains a list of properties
    try: return portage.portdb.aux_get(ebuild, [property])[0]
    except: return ''

def best(versions):
    """returns the best version in the list"""
    return portage.best(versions)

class Properties:
    """Contains all variables in an ebuild."""
    def __init__(self, dict = None):
        self.__dict = dict
        
    def __getattr__(self, name):
        try: return self.__dict[name].decode('ascii')  # return unicode
        except: return u""  # always return something
        
    def get_slot(self):
        """Return slot number as an integer."""
        try: return int(self.slot)
        except ValueError: return 0   # ?

    def get_keywords(self):
        """Returns a list of strings."""
        return self.keywords.split()

    def get_use_flags(self):
        """Returns a list of strings."""
        return self.iuse.split()

    def get_homepages(self):
        """Returns a list of strings."""
        return self.homepage.split()

def get_properties(ebuild):
    """Get all ebuild variables in one chunk."""
    dprint("PORTAGELIB: global get_properties()")
    return Properties(dict(zip(keys,
                               portage.portdb.aux_get(ebuild,
                                                      portage.auxdbkeys))))
    
def get_metadata(package):
    """Get the metadata for a package"""
    # we could check the overlay as well,
    # but we are unlikely to find any metadata files there
    try: return parse_metadata(portdir + "/" + package + "/metadata.xml")
    except: return None

class Package:
    """An entry in the package database"""

    def __init__(self, full_name):
        self.full_name = full_name
        Installed_Semaphore.acquire()
        self.is_installed = full_name in installed  # true if installed
        Installed_Semaphore.release()

    def get_installed(self):
        """Returns a list of all installed ebuilds."""
        return get_installed(self.full_name)
    
    def get_name(self):
        """Return name portion of a package"""
        return get_name(self.full_name)

    def get_category(self):
        """Return category portion of a package"""
        return get_category(self.full_name)

    def get_latest_ebuild(self, include_masked = True):
        """Return latest ebuild of a package"""
        # Note: this is slow, see get_versions()
        criterion = include_masked and 'match-all' or 'match-visible'
        return portage.best(self.get_versions(include_masked))

    def get_metadata(self):
        """Get a package's metadata, if there is any"""
        return get_metadata(self.full_name)

    def get_properties(self, specific_ebuild = None):
        """ Returns properties of specific ebuild.
           If no ebuild specified, get latest ebuild. """
	dprint("PORTAGELIB: Package:get_properties()")
        try:
            if specific_ebuild == None:
                ebuild = self.get_latest_ebuild()
            else:
                ebuild = specific_ebuild
            if not ebuild:
                raise Exception(_('No ebuild found.'))
            return get_properties(ebuild)
        except Exception, e:
            dprint("PORTAGELIB: %s" % e)  # fixed bug # 924730
            return Properties()

    def get_versions(self, include_masked = True):
        """Returns all versions of the available ebuild"""
        # Note: this slow, especially when include_masked is false
        criterion = include_masked and 'match-all' or 'match-visible'
        return portage.portdb.xmatch(criterion, self.full_name)

    def upgradable(self, upgrade_only = False):
        """Returns true if an unmasked upgrade/downgrade is available"""
        # Note: this is slow, see get_versions()
        installed = self.get_installed()
        if not installed:
            return False
        versions = self.get_versions(False);
        if not versions:
            return False
	if upgrade_only:
	    best = portage.best(installed + versions)  # upgrade only
	else:
	    best = portage.best(versions) # upgrade or downgrade
        return best not in installed


def sort(list):
    """sort in alphabetic instead of ASCIIbetic order"""
    dprint("PORTAGELIB: sort()")
    
    spam = [(x[0].upper(), x) for x in list]
    spam.sort()
    return [x[1] for x in spam]


class Database:
    def __init__(self):
        # category dictionary with sorted lists of packages
        self.categories = {}
        # all packages in a list sorted by package name
        self.list = []
        # category dictionary with sorted lists of installed packages
        self.installed = {}
        # keep track of the number of installed packages
        self.installed_count = 0
        
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
            return None


class DatabaseReader(threading.Thread):
    """Builds the database in a separate thread."""

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(1)     # quit even if this thread is still running
        self.db = Database()  # the database
        self.done = False     # false if the thread is still working
        self.count = 0        # number of packages read so far
        self.error = ""       # may contain error message after completion
        self.new_installed_Semaphore = threading.Semaphore()
        self.installed_list = None
	self.allnodes_length = 0  # used for calculating the progress bar

    def get_db(self):
        """Returns the database that was read."""
        return self.db

    def read_db(self):
        """Read portage's database and store it nicely"""
        tree = portage.db['/']['porttree']
        self.get_installed()
        try:
            dprint("PORTAGELIB: read_db(); getting allnodes package list")
            allnodes = tree.getallnodes()
	    dprint("PORTAGELIB: read_db(); Done getting allnodes package list")
        except OSError, e:
            # I once forgot to give read permissions
            # to an ebuild I created in the portage overlay.
            self.error = str(e)
            return
	self.allnodes_length = len(allnodes)
        dprint("PORTAGELIB: read_db() create internal porthole list; length=%d" %len(allnodes))
        #dsave("db_allnodes_cache", allnodes)
        for entry in allnodes:
                category, name = entry.split('/')
                # why does getallnodes() return timestamps?
                if name == 'timestamp.x' or name[-4:] == "tbz2":  
                    continue
                self.count += 1
                gtk.threads_enter()
                data = Package(entry)
                gtk.threads_leave()
                self.db.categories.setdefault(category, {})[name] = data;
                if entry in self.installed_list:
                    self.db.installed.setdefault(category, {})[name] = data;
                    self.db.installed_count += 1
                self.db.list.append((name, data))
        dprint("PORTAGELIB: read_db(); end of list build; sort is next")
        self.db.list = sort(self.db.list)

    def get_installed(self):
        """get a new installed list"""
        # I believe this next variable may be the cause of our segfaults
        # so I' am semaphoring it.  Brian 2004/08/19
        self.new_installed_Semaphore.acquire()
        #installed_list # a better way to do this?
        dprint("PORTAGELIB: get_installed();")
        self.installed_list = portage.db['/']['vartree'].getallnodes()
        gtk.threads_enter()
        global Installed_Semaphore
        global installed
        Installed_Semaphore.acquire()
        installed = self.installed_list
        Installed_Semaphore.release()
        gtk.threads_leave()
        self.new_installed_Semaphore.release()
        
    def run(self):
        """The thread function."""
        self.read_db()
        self.done = True   # tell main thread that this thread has finished




if __name__ == "__main__":
    def main():
        # test program
        debug = True
##         print (read_access() and "Read access" or "No read access")
##         print (write_access() and "Write access" or "No write access")
        import time, sys
        db_thread = DatabaseReader(); db_thread.run(); db_thread.done = True
        while not db_thread.done:
            print >>sys.stderr, db_thread.count,
            time.sleep(0.1)
        print
        db = db_thread.get_db()
        return
        while 1:
            print; print "Enter full package name:"
            queries = sys.stdin.readline().split()
            for query in queries:
                print; print query
                package = db.get_package(query)
                if not package:
                    print "--- unknown ---"
                    continue
                props = package.get_properties()
                print "Homepages:", props.get_homepages()
                print "Description:", props.description
                print "License:", props.license
                print "Slot:", props.get_slot()
                print "Keywords:", props.get_keywords()
                print "USE flags:", props.get_use_flags()
                print "Installed:", package.get_installed()
                print "Latest:", get_version(package.get_latest_ebuild())
                print ("Latest unmasked:",
                       get_version(package.get_latest_ebuild(0)))

##    main()
    import profile, pstats
    profile.run("main()", "stats.txt")

    stats = pstats.Stats("stats.txt")
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    #stats.sort_stats('time')
    #stats.sort_stats('calls')
    stats.print_stats(0.2)
