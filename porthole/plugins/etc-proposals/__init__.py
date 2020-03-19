#!/usr/bin/env python
#
'''
    Generic Porthole plug-in module.
    
    Copyright (C) 2004 - 2008 Brian Bockelman, Tommy Iorns, Brian Dolbec.

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

import os.path
from gettext import gettext as _

from porthole.utils.utils import is_root
from porthole.utils import debug
from porthole.sterminal import SimpleTerminal
from porthole.privilege import controller as privileges

app = None
manager = None
menuitem1 = False
menuitem2 = False
plugin_name = "ETC-PROPOSALS: __init__(); "
desc = _("A gtk2 alternative to etc-update or dispatch-conf")
command = "/usr/sbin/etc-proposals"
initialized = False
enabled = False
is_installed = os.path.exists(command)
debug.dprint(plugin_name + " comand: '%s' found = %s." %(command,is_installed)) 

## The next variable should be set to False if the porthole preferences are not needed
#need_prefs = False
need_prefs = True ## then import them from Config

# boolean that causes the plugin gui to load the plugin's options widget
HAS_OPTIONS = True

if need_prefs:
    from porthole import config

def new_instance(my_manager):
    global  manager, initialized, is_installed
    if not is_installed:
        debug.dprint(plugin_name + " new_instance: unable to initialze: '%s' not found" %command)
        return False
    manager = my_manager
    initialized = True
    debug.dprint(plugin_name + " new_instance: initialized okay")
    return True

def destroy_instance( ):
    global manager, initialized
    if initialized == True:
        disable_plugin()    
    manager.del_menuitem(menuitem)
    initialized = False
    debug.dprint(plugin_name + " destroy_instance: destroyed")
    return True
    
def enable_plugin():
    global menuitem1, menuitem2, enabled, initialized
    if initialized == False:
        debug.dprint(plugin_name + " enable_plugin: not initialized!")
        return False
    elif not is_installed:
        debug.dprint(plugin_name + " enable_plugin: target command not installed.")
        return False
    debug.dprint(plugin_name + " enable_plugin: generating new menuitem")
    menuitem1 = manager.new_menuitem(_("Etc-Proposals"))
    if is_root():
        debug.dprint(plugin_name + " enabling plugin to run_as_user")
        menuitem1.connect("activate", run_as_user)
    else:
        debug.dprint(plugin_name + " enabling plugin to run_as_root")
        menuitem1.connect("activate", run_as_root)
    enabled = True
    return True

def disable_plugin():
    global manager, enabled
    if initialized == False:
        return
    manager.del_menuitem(menuitem1)
    #manager.del_menuitem(menuitem2)
    enabled = False

event_table = {
	"load" : new_instance,
	"reload" : new_instance,
	"unload" : destroy_instance,
	"enable" : enable_plugin,
	"disable" : disable_plugin
}

def run_as_root(*args):
    global app, command
    if privileges.can_su:
        app = SimpleTerminal(command, True, dprint_output='Etc=proposals Plug-in;')
        app._run()
    else:
        app = SimpleTerminal(config.Prefs.globals.su + ' ' +command, True, dprint_output='Etc=proposals Plug-in;')
        app._run()

def run_as_user(*args):
	global app, command
	app = SimpleTerminal(command, False)
	app._run()

def configure_options():
	pass

