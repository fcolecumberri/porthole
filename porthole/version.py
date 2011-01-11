#!/usr/bin/env python
"""
    Porthole version
    Copyright (C) 2006 -2011 Brian Dolbec


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

#version = "0.6.1"

copyright = _("Copyright (c) 2003 - 2020")

version ="git-"

ver_info = {}


def get_git_info(prop):
    global ver_info
    if ver_info == {}:
        commit = ''
        date = ''
        branch = ''
        try:
            from subprocess import Popen, PIPE
            # fixme unused mp
            mp= os.path.dirname(os.path.abspath(__file__))
            data = Popen([b"git",b"log", b"HEAD^..HEAD"],stdout=PIPE).communicate()[0].split(b'\n')
            branches = Popen([b"git",b"branch"],stdout=PIPE).communicate()[0].split(b'\n')
        except:
            print("Error obtaining git log and branch info")

        for item in data:
            if item.startswith(b'commit'):
                commit = item.split()[-1]
            elif item.startswith(b'Date'):
                date = item.split(b":", 1)[-1].lstrip()

        branch = [x.split()[-1].strip() for x in branches if x.startswith(b'*')][0]

        ver_info['commit'] = commit[:10].decode()
        ver_info['date'] = date.decode()
        ver_info['branch'] = branch.decode()

    return ver_info[prop]

def get_version():
    global version
    if 'git' in version:
        rev = get_git_info('commit')
        login = os.getenv("LOGNAME")
        version = version + get_git_info('branch') + "-rev:" + rev + "--"+login
    return version

version = get_version()
