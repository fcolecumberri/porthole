#!/usr/bin/env python

"""
    Backends Utilities
    helper functions for the portage libraries and/or porthole

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor,
    Wm. F. Wheeler, Brian Dolbec, Tommy Iorns

    Copyright: 2005 Brian Harring <ferringb@gmail.com>
    
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
print "UTILITIES: id initialized to ", id

import os
from gettext import gettext as _

from porthole.utils import debug
from porthole import backends
portage_lib = backends.portage_lib
## circular import problem
##from porthole.db import userconfigs
USERCONFIGS = None

# And now for some code stolen from pkgcore :)
# Copyright: 2005 Brian Harring <ferringb@gmail.com>
# License: GPL2
def iter_read_bash(bash_source):
    """read file honoring bash commenting rules.  Note that it's considered good behaviour to close filehandles, as such, 
        either iterate fully through this, or use read_bash instead.
        once the file object is no longer referenced, the handle will be closed, but be proactive instead of relying on the 
        garbage collector."""
    try:
        if isinstance(bash_source, basestring):
            bash_source = open(bash_source, 'r')
        for s in bash_source:
            s=s.strip()
            if s.startswith("#") or s == "":
                continue
            yield s
        bash_source.close()
    except IOError:
        pass

def read_bash(bash_source):
	return list(iter_read_bash(bash_source))
# end of stolen code

def sort(list):
    """sort in alphabetic instead of ASCIIbetic order"""
    debug.dprint("BACKENDS Utilities: sort()")
    spam = [(x[0].upper(), x) for x in list]
    spam.sort()
    debug.dprint("BACKENDS Utilities: sort(); finished")
    return [x[1] for x in spam]

def get_sync_info():
    """gets and returns the timestamp info saved during
        the last portage tree sync"""
    debug.dprint("BACKENDS Utilities: get_sync_info();")
    last_sync = _("Unknown") + ' ' # need a space at end of string cause it will get trimmed later
    try:
        #debug.dprint("BACKENDS Utilities: get_sync_info(); timestamp path = " \
        #    + portage_lib.portdir + "/metadata/timestamp")
        f = open(portage_lib.portdir + "/metadata/timestamp")
        #debug.dprint("BACKENDS Utilities: get_sync_info(); file open")
        data = f.read()
        #debug.dprint("BACKENDS Utilities: get_sync_info(); file read")
        f.close()
        #debug.dprint("BACKENDS Utilities: get_sync_info(); file closed")
        #debug.dprint("BACKENDS Utilities: get_sync_info(); data = " + data)
        if data:
            try:
                #debug.dprint("BACKENDS Utilities: get_sync_info(); trying utf_8 encoding")
                last_sync = (str(data).decode('utf_8').encode("utf_8",'replace'))
            except:
                try:
                    #debug.dprint("BACKENDS Utilities: get_sync_info(); trying iso-8859-1 encoding")
                    last_sync = (str(data).decode('iso-8859-1').encode('utf_8', 'replace'))
                except:
                    debug.dprint("BACKENDS Utilities: get_sync_info(); Failure = unknown encoding")
        else:
            debug.dprint("BACKENDS Utilities: get_sync_info(); No data read")
    except os.error:
        debug.dprint("BACKENDS Utilities: get_sync_info(); file open or read error")
        debug.dprint("BACKENDS Utilities: get_sync_info(); error " + str(os.error))
    debug.dprint("BACKENDS Utilities: get_sync_info(); last_sync = " + last_sync[:-1])
    return last_sync[:-1]

def reduce_flags(flags):
    """function to reduce a list of 'USE' flags to their final setting"""
    myflags = []
    for x in flags:

        if x[0] == "+":
            debug.dprint("BACKENDS Utilities: USE flags should not start " + \
                "with a '+': " + x)
            x = x[1:]
            if not x:
                continue

        if x[0] == "-":
            try:
                myflags.remove(x[1:])
            except ValueError:
                pass
            #continue

        if x not in myflags:
            myflags.append(x)

    return myflags


def get_reduced_flags(ebuild):
    """function to get all use flags for an ebuild or package and reduce them to their final setting"""
    global USERCONFIGS
    if USERCONFIGS == None:  # avaoid a circular import problem
        from porthole.db import userconfigs
        USERCONFIGS = userconfigs
    # Check package.use to see if it applies to this ebuild at all
    package_use_flags = USERCONFIGS.get_user_config('USE', ebuild=ebuild)
    #debug.dprint("BACKENDS Utilities: get_reduced_flags(); package_use_flags = %s" %str(package_use_flags))
    if package_use_flags != None and package_use_flags != []:
        #debug.dprint("BACKENDS Utilities: get_reduced_flags(); adding package_use_flags to ebuild_use_flags")
        ebuild_use_flags = reduce_flags(portage_lib.SystemUseFlags + package_use_flags)
    else:
        #debug.dprint("BACKENDS Utilities: get_reduced_flags(); adding only system_use_flags to ebuild_use_flags")
        ebuild_use_flags = portage_lib.SystemUseFlags
    return ebuild_use_flags

