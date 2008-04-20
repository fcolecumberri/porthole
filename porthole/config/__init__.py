#!/usr/bin/env python

'''
    Porthole Config Package
    Holds common configuration and preferences functions for Porthole

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
print "CONFIG: id initialized to ", id

from porthole.config.configuration import PortholeConfiguration


Prefs = None # initialize, then create the real one from the porthole startup script PortholePreferences()
Config = PortholeConfiguration()
Mainwindow = None # initialize then update from mainwindow on window creation. Used as a parent window for dialogs