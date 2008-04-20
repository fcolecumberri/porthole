#!/usr/bin/env python

'''
    Porthole Package module
    Holds all portage library functions for Porthole

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

from porthole.db.database import Database, NEW, LOAD, SAVE
from porthole.db.dbreader import DatabaseReader
from porthole.utils.dispatcher import Dispatcher
from porthole.db.user_configs import UserConfigs

db = Database(LOAD)

#print "DB: load user configs"
userconfigs = UserConfigs(True)

#print str(userconfigs.db)