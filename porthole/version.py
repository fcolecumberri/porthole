#!/usr/bin/env python
"""
    Porthole version
    Copyright (C) 2006 -2010 Brian Dolbec


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
import os

version = "0.6.1"

copyright = _("Copyright (c) 2003 - 2010")

#version ="svn-"

svn_info = {}


def get_svn_info(prop):
    global svn_info
    if svn_info == {}:
        info = ''
        st = ''
        branch = ''
        try:
            from subprocess import Popen, PIPE
            # back up to trunk to catch all relevant svn data
            mp= os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            os.chdir(mp)
            branch = os.path.split(mp)[1]
            info = Popen(["svn","info"],stdout=PIPE).communicate()[0].split('\n')
            st = Popen(["svn","st"],stdout=PIPE).communicate()[0].split('\n')
        except:
            print "Error importing subprocess module"
            #from os import popen, PIPE

        for item in info:
            if item:
                values = item.split(':')
                svn_info[values[0]] = values[1]
        mods = []
        for line in st:
            if line.startswith('M'):
                mods.append(line.split()[1])
            elif line.startswith('A'):
                mods.append('+' + line.split()[1])
            elif line.startswith('D'):
                mods.append('-' + line.split()[1])
        svn_info['mod-files'] = mods
        svn_info['branch'] = branch
    return svn_info[prop]

def get_version():
    global version
    if 'svn' in version:
        rev = get_svn_info('Revision').strip()
        login = os.getenv("LOGNAME")
        version = version + get_svn_info('branch') + "-rev:" + rev + "--"+login
        mods = get_svn_info('mod-files')
        if mods:
            version = version + "\nModified files: " + ", ".join(mods)
    return version
    
version = get_version()
