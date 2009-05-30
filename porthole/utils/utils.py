#!/usr/bin/env python

'''
    Porthole Utils Module
    Holds common functions for Porthole

    Copyright (C) 2003 - 2009 Fredrik Arnerup, Daniel G. Taylor
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


import os, threading
import errno
import string
import re
import datetime
from sys import stderr
import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk
import grp
import pwd, cPickle
from gettext import gettext as _

from porthole.version import version
from porthole._xml.xmlmgr import XMLManager, XMLManagerError
from porthole import config
from porthole.utils import debug

def get_icon_for_package(package):
    """Return an icon for a package"""
    # if it's installed, find out if it can be upgraded
    if package and package.get_installed():
        icon = gtk.STOCK_YES
    else:
        # just put the STOCK_NO icon
        # switched to blank icon if not installed
        icon = '' # gtk.STOCK_NO
    return icon       

def get_icon_for_upgrade_package(package):
    """Return an icon and foreground text color for a package"""
    if not package:
        return '', 'blue'
    #  find out if it can be upgraded
    if package.is_upgradable() == 1:  # 1 for only upgrades (no downgrades)
        icon = gtk.STOCK_GO_UP
        color = config.Prefs.views.upgradable_fg
    else: # it's a downgrade
        icon = gtk.STOCK_GO_DOWN
        color = config.Prefs.views.downgradable_fg
    return icon, color      

def is_root():
    """Returns true if process runs as root."""
    return os.geteuid() == 0
    
write_access = is_root()

def read_access():
    """Return true if user is root or a member of the portage group."""
    # Note: you don't have to be a member of portage to read the database,
    # but portage caching will not work
    portage = 250  # is portage guaranteed to be 250?
    # answer: portage.portage_gid
    try: portage = grp.getgrnam("portage")[2]
    except: pass
    return write_access() or (portage in (os.getgroups() + [os.getegid()]))

sudo_x_ok = os.access('/usr/bin/sudo', os.X_OK)

def can_sudo():
    """ return True if /usr/bin/sudo exists and is executable """
    return sudo_x_ok
    #return False # for testing

gksudo_x_ok = os.access('/usr/bin/gksudo', os.X_OK)
gksu_x_ok = os.access('/usr/bin/gksu', os.X_OK)
gnomesu_x_ok = os.access('/usr/bin/gnomesu', os.X_OK)
kdesu_x_ok = os.access('/usr/bin/kdesu', os.X_OK)

def can_gksu(specific=None):
    if not specific:
        return gksudo_x_ok or gksu_x_ok or gnomesu_x_ok or kdesu_x_ok
    if specific == 'gksudo':
        return gksudo_x_ok
    if specific == 'gksu':
        return gksu_x_ok
    if specific == 'gnomesu':
        return gnomesu_x_ok
    if specific == 'kdesu':
        return kdesu_x_ok
    return None

def get_treeview_selection( treeview, num = None):
        """Get the value of whatever is selected in a treeview,
        num is the column, if num is nothing, the iter is returned"""
        model, iter = treeview.get_selection().get_selected()
        selection = iter
        if iter:
            if num:
                selection = model.get_value(iter, num)
        return selection

def get_user_home_dir():
    """Return the path to the current user's home dir"""
    return pwd.getpwuid(os.getuid())[5]

def environment():
    """sets up the environment to run sub processes"""
    env = os.environ
    #debug.dprint("UTILS: environment(), env before & after our additions")
    #debug.dprint(env)
    if "FEATURES" in env:
        env["FEATURES"] += ", notitles"
    else:
        env ["FEATURES"] = "notitles"
    if "PORTAGE_ELOG_SYSTEM" in env:
        modules = env["PORTAGE_ELOG_SYSTEM"].split()
        if 'echo' in modules:
            modules.remove('echo')
            env["PORTAGE_ELOG_SYSTEM"] = ' '.join(modules)
            debug.dprint("UTILS: environment(); Found 'echo' in PORTAGE_ELOG_SYSTEM. Removed for porthole's use only, it now is: " + str(env["PORTAGE_ELOG_SYSTEM"]))
    #env["NOCOLOR"] = "true"
    #debug.dprint(env)
    return env


class BadLogFile(Exception):
    """ Raised when we encounter errors parsing the log file."""

def estimate(package_name, log_file_name="/var/log/emerge.log"):
    """ Estimates, based on previous emerge operations, how long it would
        take to compile a particular package on the system. 
        
        This function returns a 4-tuple with floating point values representing
        the average duration of the compilation of a package.

        When unable to determine an average, the function returns None. """
    try:
        start_time = 0.0
        end_time = 0.0
        total_time = datetime.timedelta()
        emerge_count = 0
        log_file = open(log_file_name)       
        package_name_escaped = ""      
        # Let's excape characters like + before we try to compile the regular
        #expression
        for i in range(0, len(package_name)):
            if package_name[i] == "+" or package_name[i] == "-":
                package_name_escaped += "\\"
            package_name_escaped += package_name[i]
        # Now that we already escaped the "special characters", we
        # can start searching the logs
        start_pattern = re.compile("^[0-9]+:  >>> emerge.*%s*." %
                                                           package_name_escaped)
        end_pattern = re.compile("^[0-9]+:  ::: completed emerge.*%s*." %
                                                           package_name_escaped)      
        lines = log_file.readlines()
        for i in range(1, len(lines)):
            if start_pattern.match(lines[i]):
                tokens = lines[i].split()
                #start_time = string.atof((tokens[0])[0:-1])               
                start_time = float((tokens[0])[0:-1])               
                for j in range(i+1, len(lines)):
                    if start_pattern.match(lines[j]):
                        # We found another start pattern before finding an 
                        # end pattern.  That probably means emerge died before
                        # finishing what it was doing.
                        # We'll ignore it and continue searching. 
                        break
                    if end_pattern.match(lines[j]):                 
                        # Looks like we found a matching end statement.
                        tokens = lines[j].split()
                        #end_time = string.atof((tokens[0])[0:-1])
                        end_time = float((tokens[0])[0:-1])
                        emerge_count += 1
                        total_time = total_time +\
                                (datetime.datetime.fromtimestamp(end_time) -
                                datetime.datetime.fromtimestamp(start_time))
                        break
        if emerge_count > 0:
            return total_time / emerge_count
        else:
            return None          
    except:
        raise BadLogFile, _("Error reading emerge log file.  Check file permissions, or check for corrupt log file.")

def pretend_check(command_string):
    isPretend = (re.search("--pretend", command_string) != None)
    if not isPretend:
        tmpcmdline = command_string.replace('sudo -p "Password: "', "").split()
        #debug.dprint(tmpcmdline)
        for x in tmpcmdline:
            if x[0:1]=="-"and x[1:2]!="-":
                for y in x[1:]:
                    #debug.dprint(y)    
                    if y == "p":
                        #debug.dprint("found it")
                        isPretend = True
    return isPretend

def help_check(command_string):
    return (re.search("--help", command_string) != None)

def info_check(command_string):
    return (re.search("emerge info", command_string) != None)

def get_set_name(file):
        if file:
            return file.split('/sets/')[-1].replace("/","-")
