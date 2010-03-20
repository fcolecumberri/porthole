#!/usr/bin/env python

'''
    Porthole Utils, Permissions Submodule
    Holds user permissions functions for Porthole

    Copyright (C) 2010 Brian Dolbec

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

import os, pwd
from operator import itemgetter
from sys import stderr

"""pwd param definitions for easy clear access"""
LOGNAME = 0
PASSWD = 1
UID = 2
GID = 3
USERNAME = 4
DIR = 5
SHELL = 6


class Stack(list):
    """simple stack (list subclass) that defines push(), top, bottom,
    previuos.  Also defines 2 functions to retieve only 1 property of 
    the top's data tuple"""
    
    top = property(itemgetter(-1))
    bottom = property(itemgetter(0))
    push = list.append
    
    def __init__(self):
        list.__init__(self)

    def module(self):
            return  self.top[0]

    def privilege(self):
        return  self.top[1]


class PrivilegeControl(object):
    
    user = ''
    user_pwd = None
    
    def __init__(self, privileged):
        """No input initialization parameters."""
        self.privileged = privileged
        self.nobody_pwd = pwd.getpwnam( 'nobody' )
        self.portage_pwd = pwd.getpwnam( 'portage')
        self.priv_pwd = pwd.getpwuid(0)
        self.cntl_stack = Stack()
        self.can_su = os.getuid() == 0

    def get_user(self, param):
        return self.user_pwd[param]

    def set_user(self, user):
        """Set the initiating user name, uid, gid. Other than during
        startup priveleges will be handled here except for forked processes.
        They get privileged autamatically."""
        print  >>stderr, "PrivilegeControl: set_user(); new user: ", user
        if user:
            try:
                self.user = user
                self.user_pwd = pwd.getpwnam( user )
                self.user_uid = self.user_pwd[UID]
                self.user_gid = self.user_pwd[GID]
                print  >>stderr, "PrivilegeControl: set_user(); " +\
                    "successfully set user: ", user
            except KeyError:
                print  >>stderr, "PrivilegeControl: set_user(); " +\
                    "Unknown user: ", user
                self.user = ''
        else:
            raise Exception("Attempted to set user=None error")

    def set_privileges(self, privilege, _module):
        """Sets the effective user id and group to
        one of three possible [root, user, nobody]
        But must have either started porthole as root or su'd it
        at time of startup"""
        print  >>stderr, "PrivilegeControl: set_privileges(); " +\
            "new setting, %s, %s" %(privilege, _module)
        if self.can_su and _module in self.privileged:
            print  >>stderr, "PrivilegeControl: set_privileges(); " +\
                "trying to set new"
            try:
                if getattr(self, '_run_as_%s_' %privilege)():
                    self.cntl_stack.push((_module, privilege))
                    return True
            except Exception, error:
                raise Exception('PrivilegeControl: set_user(); Error in ' +
                    'setting privileges.\nError was:\n' + str(error))
        return False

    def end_privileges(self, _module):
        """Ends the privileged effective user id and group, resets to the
        previuos 
        """
        print  >>stderr, "PrivilegeControl: end_privileges(); " +\
            "ending: %s" %_module
        if self.can_su and _module == self.cntl_stack.module():
            (mod, priv) = self.cntl_stack.pop()
            return getattr(self, '_run_as_%s_' %self.cntl_stack.privilege())()
        return False

    def _run_as_nobody_(self):
        """Switch this process to normal privileges, we shouldn't be able to
        do anything naughty in this mode."""
        print >>stderr, "PrivilegeControl: _run_as_nobody_()"
        try:
            if os.geteuid() != 0:
                os.seteuid(0)
            os.setegid( self.nobody_pwd[GID] )
            os.seteuid( self.nobody_pwd[UID] )
        except:
            return False
        return True


    def _run_as_root_(self):
        """Switch to super user privileges, here we can do anything we want."""
        print >>stderr, "PrivilegeControl: _run_as_privileged_()"
        try:
            os.seteuid( self.priv_pwd[UID] )
            os.setegid( self.priv_pwd[GID] )
        except:
            return False
        return True

    def _run_as_user_(self):
        """Switch to originating users id & priveleges"""
        print >>stderr, "PrivilegeControl: _run_as_user_()"
        try:
            print "PrivilegeControl: _run_as_user_(); setting euid"
            if os.geteuid() != 0:
                os.seteuid(0)
            os.setegid( self.user_pwd[GID])
            os.seteuid( self.user_pwd[UID] )
        except:
            return False
        return True

    def _run_as_portage_(self):
        """Switch to originating users id & priveleges"""
        print >>stderr, "PrivilegeControl: _run_as_portage_()"
        try:
            print "PrivilegeControl: _run_as_portage_(); setting to portage egid, user ueuid"
            if os.geteuid() != 0:
                os.seteuid(0)
            os.setegid(self.portage_pwd[GID])
            os.seteuid( self.user_pwd[UID] )
        except:
            return False
        return True


controller = PrivilegeControl(
    privileged= ['startup', 'set_config', 'version', 'mainwindow', 'loaders'])

def get_user_home_dir():
    """Return the path to the current user's home dir"""
    return controller.user_pwd[DIR]
