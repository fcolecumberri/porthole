#!/usr/bin/env python

'''
    Porthole debug module
    Holds common debug functions for Porthole

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor
    Brian Dolbec, Wm. F. Wheeler, Tommy Iorns

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

import datetime
id = datetime.datetime.now().microsecond
print "DEBUG: id initialized to ", id

import errno
import string
#import re
from sys import stderr
import pwd, cPickle
import os


def __dummy(*args):
    pass

global dprint, dsave, debug, debug_target

# initially set debug to false
debug = False
debug_target = "ALL"

    
# initialize to dummy functions
dprint = __dummy
dsave = __dummy 

def set_debug(mode):
    global debug, dprint, dsave
    if mode:
        dprint = _dprint
        dsave = _dsave
    else:
        dprint = __dummy 
        dsave = __dummy
    debug = mode
    
def _dprint(message):
	"""Print debug message if debug is true."""
	#print >>stderr, message
	if debug_target == "ALL" or debug_target in message:
		print >>stderr, message
	#else:
	#    print >>stderr, "message filtered"

def _dsave(name, item = None):
	"""saves 'item' to file 'name' if debug is true"""
	_dprint("UTILS: dsave() Pickling 'item' to file: %s" %name)
	# get home directory
	home = pwd.getpwuid(os.getuid())[5]
	# pickle it baby, yeah!
	cPickle.dump(item, open(home + "/.porthole/" + name, "w"))

