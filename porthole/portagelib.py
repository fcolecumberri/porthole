#!/usr/bin/env python

"""
    PortageLib
    An interface library to Gentoo's Portage

    Copyright (C) 2003 - 2004 Fredrik Arnerup and Daniel G. Taylor

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
from utils import dprint
import string
from string import digits, zfill
try:
    import portage
except ImportError:
    exit('Could not find portage module.\n'
         'Are you sure this is a Gentoo system?')

import threading
from metadata import parse_metadata

def get_portage_environ(var):
    """Returns environment variable from portage if possible, else None"""
    try: temp = portage.config(clone=portage.settings).environ()[var]
    except: temp = None
    return temp

portdir = portage.config(clone=portage.settings).environ()['PORTDIR']
# is PORTDIR_OVERLAY always defined?
portdir_overlay = get_portage_environ('PORTDIR_OVERLAY')
    
# lower case is nicer
keys = [key.lower() for key in portage.auxdbkeys]

# a list of all installed packages
installed = None
        
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
        self.is_installed = full_name in installed  # true if installed

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

    def get_properties(self):
        """Returns properties of latest ebuild."""
        try:
            latest = self.get_latest_ebuild()
            if not latest:
                raise Exception('No ebuild found.')
            return get_properties(latest)
        except Exception, e:
            dprint("PORTAGELIB: %s" % e)  # fixed bug # 924730
            return Properties()

    def get_versions(self, include_masked = True):
        """Returns all versions of the available ebuild"""
        # Note: this slow, especially when include_masked is false
        criterion = include_masked and 'match-all' or 'match-visible'
        return portage.portdb.xmatch(criterion, self.full_name)

    def upgradable(self):
        "Returns true if an unmasked upgrade is available"
         # Note: this is slow, see get_versions()
        installed = self.get_installed()
        if not installed:
            return False
        versions = self.get_versions(False);
        if not versions:
            return False
        best = portage.best(installed + versions)
        return best not in installed

def split_digits(a_string):
    """splits the string at letter/digit boundaries"""
    #dprint("PORTAGELIB: split_digits()")
    # short circuit for  length of 1
    if len(a_string)==1:
        return [a_string]
    #dprint(a_string)
    result = []
    s = ''
    is_digit = (a_string[0] in digits)
    #dprint(is_digit)
    for x in a_string:
        if (x in digits) == is_digit:
            s += x
        else:
            result += [s]
            s = x
            is_digit = (x in digits)
    result += [s]
    #dprint("PORTAGELIB: split_digits()  result[]")
    #dprint(result)
    return result
        

def pad_ver(vlist):
    """pads the version string so all number sequences are the same
       length for acurate sorting, borrowed & modified code from portage"""
    #dprint("PORTAGELIB: pad_ver()  vlist[]")
    #dprint(vlist)
    # short circuit for  list of 1
    if len(vlist) == 1:
        return vlist

    max_length = 0
    val_cache = []
    prepart_cache = []

    for val1 in vlist:
        # consider 1_p2 vc 1.1
        # after expansion will become (1_p2,0) vc (1,1)
        # then 1_p2 is compared with 1 before 0 is compared with 1
        # to solve the bug we need to convert it to (1,0_p2)
        # by splitting _prepart part and adding it back _after_expansion
        val1_prepart = ''
        if val1.count('_'):
                val1, val1_prepart = val1.split('_', 1)

        # replace '-' by '.'
        # FIXME: Is it needed? can val1/2 contain '-'?
        val1=string.split(val1,'-')
        if len(val1)==2:
                val1[0]=val1[0]+"."+val1[1]

        val1=string.split(val1[0],'.')

        # track the maximum length we need to pad to
        max_length = max(len(val1), max_length)
                         
        #temp store the data until the end of the list
        val_cache += [val1]
        prepart_cache += [val1_prepart]

    result = []
    for x in range(0,len(val_cache)):
        # extend version numbers
        if len(val_cache[x])< max_length:
                val_cache[x].extend(["0"]*(max_length-len(val_cache[x])))
        # fill numbers with leading zero's
        #dprint("zfill")
        new_val = []
        for y in val_cache[x]:
            #dprint(val_cache[x])
            #dprint(y)
            y = split_digits(y)
            tmp = []
            for z in y:
                if z[0] in digits:
                    tmp += [zfill(z, 3)]
                else:
                    tmp += [z]
            new_val += [string.join(tmp, "")]
            #dprint("zfill = ")
            #dprint(new_val)
            
        # add back _prepart tails
        if prepart_cache[x]:
            new_pre = ''
            y = split_digits(prepart_cache[x])
            tmp = []
            for z in y:
                if z[0] in digits:
                    tmp += [zfill(z, 3)]
                else:
                    tmp += [z]
            new_pre += string.join(tmp, "")
            new_val[-1] = '_' + new_pre
            #dprint("new_pre[]")
            #dprint(new_pre)
        #The above code will extend version numbers out so they
        #have the same number of digits
        new_val = string.join(new_val, ".")
           
        result += [new_val]

    #dprint("PORTAGELIB: pad_ver() result[]")
    #dprint(result)
    return result

def sort(list):
    """sort in alphabetic instead of ASCIIbetic order"""
    dprint("POTAGELIB: sort()")
    
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

    def get_db(self):
        """Returns the database that was read."""
        return self.db

    def read_db(self):
        """Read portage's database and store it nicely"""
        tree = portage.db['/']['porttree']
        global installed # what's a better way to do this?
        installed = portage.db['/']['vartree'].getallnodes()
        try:
            allnodes = tree.getallnodes()
        except OSError, e:
            # I once forgot to give read permissions
            # to an ebuild I created in the portage overlay.
            self.error = str(e)
            return
        for entry in allnodes:
            category, name = entry.split('/')
            # why does getallnodes() return timestamps?
            if name == 'timestamp.x' or name[-4:] == "tbz2":  
                continue
            self.count += 1
            data = Package(entry)
            self.db.categories.setdefault(category, {})[name] = data;
            if entry in installed:
                self.db.installed.setdefault(category, {})[name] = data;
                self.db.installed_count += 1
##                 if data.upgradable():
##                     self.db.upgradable.append((name, data))
            self.db.list.append((name, data))
        self.db.list = sort(self.db.list)
##        self.db.upgradable = sort(self.db.upgradable)
        
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
