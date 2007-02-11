#!/usr/bin/env python

'''
    Porthole backend module
    Holds all portage and related library functions for Porthole

    Copyright (C) 2003 - 2006 Fredrik Arnerup, Daniel G. Taylor
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

import config
from importer import my_import

print "PORTAGE setting = ", config.Prefs.PORTAGE

#import portagelib as portage_lib
portage_lib = my_import(config.Prefs.PORTAGE)

print "BACKENDS: portage_lib import complete :", portage_lib

del config
del my_import


