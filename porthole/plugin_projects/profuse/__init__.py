#!/usr/bin/env python
#
'''
    Generic Porthole plug-in module.
    
    Copyright (C) 2004 - 2005 Brian Bockelman, Tommy, Brian Dolbec.

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


import utils
from utils import dprint
from gettext import gettext as _
from sterminal import SimpleTerminal


app = None
manager = None
menuitem1 = False
menuitem2 = False
plugin_name = "PROFUSE: __init__; "
desc = _("Edit USE Variables settings using the Profuse editor")
command = "profuse"
initialized = False
enabled = False
## The next variable should be set to False if the porthole preferences are not needed
#need_prefs = False
need_prefs = True ## then plugin.py will push them here during initialzation
prefs = None

def new_instance(my_manager):
    global  manager, initialized
    manager = my_manager
    initialized = True
    dprint(plugin_name + " new_instance: initialized okay")
    return True

def destroy_instance( ):
    global manager, initialized
    if initialized == True:
        disable_plugin()    
    manager.del_menuitem(menuitem)
    initialized = False
    dprint(plugin_name + " destroy_instance: destroyed")
    return True
    
def enable_plugin():
    global menuitem1, menuitem2, enabled, initialized
    if initialized == False:
        dprint(plugin_name + " enable_plugin: not initialized!")
        return False
    dprint(plugin_name + " enable_plugin: generating new menuitem")
    menuitem1 = manager.new_menuitem(_("Profuse (user mode)"))
    menuitem1.connect("activate", run_as_user)
    menuitem2 = manager.new_menuitem(_("Profuse (su mode)"))
    menuitem2.connect("activate", run_as_root)
    enabled = True
    return True

def disable_plugin():
    global manager, enabled
    if initialized == False:
        return
    manager.del_menuitem(menuitem1)
    manager.del_menuitem(menuitem2)
    enabled = False

event_table = {
	"load" : new_instance,
	"reload" : new_instance,
	"unload" : destroy_instance,
	"enable" : enable_plugin,
	"disable" : disable_plugin
}

def run_as_root(*args):
	global app, command, prefs
	app = SimpleTerminal(prefs.globals.su + ' ' + command, False)
	app._run()

def run_as_user(*args):
	global app, command
	app = SimpleTerminal(command, False)
	app._run()

