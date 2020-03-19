#!/usr/bin/env python

'''
    Porthole backend module
    Holds all portage and related library functions for Porthole

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
print "BACKENDS: id initialized to ", id

import time

portage_lib = None

def load(pmslib):
    global portage_lib
    if pmslib == "portagelib":
        from porthole.backends import portagelib
        portage_lib = portagelib
        print "BACKENDS: portage_lib import complete :", portage_lib



