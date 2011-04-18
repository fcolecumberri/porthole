#!/usr/bin/env python

'''
    Porthole Plugin Interface
    Imports and interacts with plugins

    Copyright (C) 2003 - 2008 Brian Bockelman, Brian Dolbec, Tommy Iorns

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

import datetime
id = datetime.datetime.now().microsecond
print "PLUGIN: id initialized to ", id

import os
#import imp

#from porthole.utils import utils
from porthole.utils import debug
#from porthole.importer import my_import
from porthole import config

class PluginManager:
    """Handles all of our plugins"""
    def __init__(self, porthole_instance, ):
        #Scan through the contents of the directories
        #Load any plugins it sees
        #self.path_list = path_list
        plugin_dir = config.Prefs.PLUGIN_DIR
        self.porthole_instance = porthole_instance
        self.plugins = []
        plugin_list = []
        list = os.listdir(plugin_dir)
        for entry in list:
            debug.dprint("PLUGIN: PluginManager.init();"
                " possible plugin found: %s" % entry)
            if os.path.isdir(os.path.join(plugin_dir, entry)):
                if os.access(os.path.join(plugin_dir, entry, '__init__.py'),
                        os.R_OK):
                    plugin_list.append(entry)
                    debug.dprint("PLUGIN: PluginManager.init();"
                        " valid plugin found: %s" % entry)
        os.chdir(plugin_dir)
        for entry in plugin_list:
            new_plugin = Plugin(entry, plugin_dir, self)
            self.plugins.append(new_plugin)
        self.event_all("load", self)

    def event_all(self, event, *args):
        for i in self.plugins:
            i.event(event, *args)
            #We should really check our prefs here to see if they should
            # automatically be enabled.
            i.enabled = i.name in config.Prefs.plugins.active_list
            if i.enabled:
                i.event("enable")

    def plugin_list(self):
        return self.plugins

    def new_menuitem(self, label):
        menuitem = self.porthole_instance.new_plugin_menuitem(label)
        return menuitem

    def del_menuitem(self, menuitem):
        self.porthole_instance.del_plugin_menuitem(menuitem)

    def new_package_tab(self, *args):
        #I separate the main window from the plugins in case if we ever
        #want to execute the plugins in a separate thread
        return self.porthole_instance.new_plugin_package_tab(*args)

    def del_package_tab(self, *args):
        return self.porthole_instance.del_plugin_package_tab(*args)

    def new_view(self, *args):
        #I separate the main window from the plugins in case if we ever
        #want to execute the plugins in a separate thread
        return self.porthole_instance.new_plugin_view(*args)

    def del_view(self, *args):
        return self.porthole_instance.del_plugin_view(*args)

    def destroy(self):
        for i in self.plugins:
            i.event("unload")

    def get_plugin(self, plugin_name):
        for i in self.plugins:
            if i.name == plugin_name:
                return i
        return None

class Plugin:
    """Class that defines all of our plugins"""
    def __init__(self, name, path, manager):
        debug.dprint("PLUGIN: init(); New plugin being made:"
            " '%(name)s' in %(path)s" % locals())
        self.name = name
        self.path = path
        self.event_table = {}
        self.manager = manager
        initialized = self.initialize_plugin()
        self.enabled = False
        self.is_installed = None

    def initialize_plugin(self):
        try:
            os.chdir(self.path)
            debug.dprint("PLUGIN: initialize_plugin;"
                " cwd: %s !!!!!!!!!!!!!!!!!" % os.getcwd())
            #find_results = imp.find_module(self.name, self.path)
            #self.module = imp.load_module(self.name, *find_results)
            #plugin_name = self.path + self.name
            plugin_name = '.'.join(['porthole','plugins', self.name])
            debug.dprint('Plugin name = ' + plugin_name)
            #
            #self.module = my_import(plugin_name)
            self.module = __import__(plugin_name, [], [], ['not empty'])
            debug.dprint('Plugin module = ' + str(self.module))
            self.valid = True
        except ImportError, e:
            debug.dprint("PLUGIN: initialize_plugin(); ImportError '%s'" % e)
            debug.dprint("PLUGIN: initialize_plugin(); Error loading plugin"
                " '%s' in %s" % (self.name, self.path))
            self.valid = self.is_installed = False
            return False
        debug.dprint("PLUGIN: initialize_plugin(); !!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.event_table = self.module.event_table
        self.desc = self.module.desc
        self.is_installed = self.module.is_installed
        debug.dprint(
            "PLUGIN: %s event_table = %s" %(self.name, str(self.event_table)))
        debug.dprint("PLUGIN: %s desc = %s" %(self.name, str(self.desc)))
        debug.dprint(
            "PLUGIN: %s is_installed = %s" %(self.name, str(self.is_installed)))
        if not self.is_installed:
            self.enabled = False
            self.event("disable")

    def toggle_enabled(self):
        if self.enabled == True:
            self.enabled = False
            self.event("disable")
        else:
            self.enabled = True
            self.event("enable")

    def event(self, event, *args):
        debug.dprint("PLUGIN: Event: " + event + ", Plugin: " + self.name)
        if event in self.event_table:
            a = self.event_table[event](*args)
        else:
            a = None
            debug.dprint("PLUGIN: event():"
                " %s , not defined for plugin: %s" %(event,self.name))
            debug.dprint(
                "PLUGIN: event(): event_table = " + str(self.event_table))
            return a
        if not a:
            debug.dprint("PLUGIN: event: recieved"
                " '%s' as response from %s" %(str(a), self.name))
        return a
        #return self.event_table[event](*args)

