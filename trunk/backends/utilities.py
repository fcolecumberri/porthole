#!/usr/bin/env python

"""
    Backends Utilities
    helper functions for the portage libraries and/or porthole

    Copyright (C) 2003 - 2006 Fredrik Arnerup, Daniel G. Taylor,
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

from gettext import gettext as _

import utils.debug
import os
import backends
portage_lib = backends.portage_lib

# And now for some code stolen from pkgcore :)
# Copyright: 2005 Brian Harring <ferringb@gmail.com>
# License: GPL2
def iter_read_bash(bash_source):
	"""read file honoring bash commenting rules.  Note that it's considered good behaviour to close filehandles, as such, 
	either iterate fully through this, or use read_bash instead.
	once the file object is no longer referenced, the handle will be closed, but be proactive instead of relying on the 
	garbage collector."""
	if isinstance(bash_source, basestring):
		bash_source = open(bash_source, 'r')
	for s in bash_source:
		s=s.strip()
		if s.startswith("#") or s == "":
			continue
		yield s
	bash_source.close()

def read_bash(bash_source):
	return list(iter_read_bash(bash_source))
# end of stolen code

def sort(list):
    """sort in alphabetic instead of ASCIIbetic order"""
    utils.debug.dprint("BACKENDS Utilities: sort()")
    spam = [(x[0].upper(), x) for x in list]
    spam.sort()
    utils.debug.dprint("BACKENDS Utilities: sort(); finished")
    return [x[1] for x in spam]

def get_sync_info():
    """gets and returns the timestamp info saved during
        the last portage tree sync"""
    utils.debug.dprint("BACKENDS Utilities: get_sync_info();")
    last_sync = _("Unknown") + ' ' # need a space at end of string cause it will get trimmed later
    try:
        #utils.debug.dprint("BACKENDS Utilities: get_sync_info(); timestamp path = " \
        #    + portage_lib.portdir + "/metadata/timestamp")
        f = open(portage_lib.portdir + "/metadata/timestamp")
        #utils.debug.dprint("BACKENDS Utilities: get_sync_info(); file open")
        data = f.read()
        #utils.debug.dprint("BACKENDS Utilities: get_sync_info(); file read")
        f.close()
        #utils.debug.dprint("BACKENDS Utilities: get_sync_info(); file closed")
        #utils.debug.dprint("BACKENDS Utilities: get_sync_info(); data = " + data)
        if data:
            try:
                #utils.debug.dprint("BACKENDS Utilities: get_sync_info(); trying utf_8 encoding")
                last_sync = (str(data).decode('utf_8').encode("utf_8",'replace'))
            except:
                try:
                    utils.debug.dprint("BACKENDS Utilities: get_sync_info(); trying iso-8859-1 encoding")
                    last_sync = (str(data).decode('iso-8859-1').encode('utf_8', 'replace'))
                except:
                    utils.debug.dprint("BACKENDS Utilities: get_sync_info(); Failure = unknown encoding")
        else:
            utils.debug.dprint("BACKENDS Utilities: get_sync_info(); No data read")
    except os.error:
        utils.debug.dprint("BACKENDS Utilities: get_sync_info(); file open or read error")
        utils.debug.dprint("BACKENDS Utilities: get_sync_info(); error " + str(os.error))
    utils.debug.dprint("BACKENDS Utilities: get_sync_info(); last_sync = " + last_sync[:-1])
    return last_sync[:-1]


