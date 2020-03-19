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

import os, os.path
from gettext import gettext as _
#from multiprocessing import Process

from porthole.utils.utils import is_root, environment
from porthole.utils import debug
from porthole.sterminal import SimpleTerminal
from porthole.privilege import controller as privileges

app = None
manager = None
menuitem1 = False
menuitem2 = False
plugin_name = "Gpytage: __init__(); "
desc = _("A gtk2 specialty editor for /etc/portage/ files")
command = "/usr/bin/gpytage"
initialized = False
enabled = False
is_installed = os.path.exists(command)
debug.dprint(plugin_name + " command: '%s' found = %s." %(command,is_installed)) 

## The next variable should be set to False if the porthole preferences are not needed
#need_prefs = False
need_prefs = True ## then import them from Config

# boolean that causes the plugin gui to load the plugin's options widget
HAS_OPTIONS = False


if need_prefs:
    #global RUN_LOCAL
    from porthole import config
    
debug.dprint(plugin_name + 
    "config.Prefs.RUN_LOCAL= %s" %str(config.Prefs.RUN_LOCAL)) 
if config.Prefs.RUN_LOCAL:
    #global command
    import sys
    # make a destructable copy
    paths = environment()["PATH"].split(":")
    #debug.dprint(plugin_name + "paths = %s" %str(paths))
    found_local = False
    while paths and not found_local:
        this_path = paths[0]
        paths.remove(this_path)
        #debug.dprint(plugin_name + "this_path = " + this_path) 
        if "/home/" in this_path  \
                and "gpytage" in this_path \
                and this_path.endswith("scripts"):
            found_local = True
            is_installed = True
            command = '"' + os.path.join(this_path, "gpytage") +'"'
            debug.dprint(plugin_name + " Found local version of Gpytage to run :)")
            debug.dprint(plugin_name + " local command: '%s' found = %s." %(command,is_installed)) 
        elif 'site-packages' in this_path:
            # found a normal python path before a local one
            debug.dprint(plugin_name + " I DID NOT Find a local version of Gpytage to run :(")
            break

debug.dprint(plugin_name + " final command: '%s' found = %s." %(command,is_installed)) 


def main_callback(*arg, **kwargs):
    """callback from mainwindow to process requests, pass info..."""
    pass

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
    menuitem1 = manager.new_menuitem(_("Gpytage"))
    #config_path = os.path.join(portage_lib.settings.config_root, portage_lib.settings.user_config_dir)
    #if os.access(config_path, os.W_OK):
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
    debug.dprint(plugin_name + " running command: '%s'" %(command)) 
    if privileges.can_su:
        app = SimpleTerminal(command, True, dprint_output='Gpytage Plug-in;')
        app._run()
    else:
        app = SimpleTerminal(config.Prefs.globals.su + ' ' +command, True, dprint_output='Gpytage Plug-in;')
        app._run()

def run_as_user(*args):
    global app, command
    app = SimpleTerminal(command, True, dprint_output='Gpytage Plug-in;')
    app._run()

def configure_options():
    pass

