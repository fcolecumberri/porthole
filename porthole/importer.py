#!/usr/bin/env python

"""
    
    Importer modules for dynamic module importing.

    Copyright (C) 2006 -2008 Brian Dolbec


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

# taken from the python reference on the __import__()
# returns the last module in the name as __import__ only returns the first one

def my_import(name):
    print "IMPORTER: name = ", name
    mod = __import__(name)
    print "IMPORTER: mod = ", mod
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
        print "IMPORTER: mod = ", mod
    return mod
    
