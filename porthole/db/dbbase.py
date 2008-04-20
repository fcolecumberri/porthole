#!/usr/bin/env python

"""
    Package Database structure

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor,
    Wm. F. Wheeler, Brian Dolbec, Tommy Iorns


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



class DBBase:
    def __init__(self):
        # category dictionary with sorted lists of packages
        self.categories = {}
        # all packages in a list sorted by package name
        self.list = []
        # category dictionary with sorted lists of installed packages
        self.installed = {}
        # keep track of the number of installed packages
        self.installed_count = 0
        # the next 2 tuples hold pkg counts for each category
        self.pkg_count = {}
        self.installed_pkg_count = {}
        self.depricated_list = []
