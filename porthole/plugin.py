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
from glob import glob
import gtk
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
            debug.dprint("PLUGIN: PluginManager.init(); possible plugin found: %s" % entry)
            if os.path.isdir(os.path.join(plugin_dir, entry)):
                if os.access(os.path.join(plugin_dir, entry, '__init__.py'), os.R_OK):
                    plugin_list.append(entry)
                    debug.dprint("PLUGIN: PluginManager.init(); valid plugin found: %s" % entry)
        os.chdir(plugin_dir)
        for entry in plugin_list:
            new_plugin = Plugin(entry, plugin_dir, self)
            self.plugins.append(new_plugin)
        self.event_all("load", self)

    def event_all(self, event, *args):
        for i in self.plugins:
            i.event(event, *args)
            #We should really check our prefs here to see if they should automatically be enabled.
            i.enabled = i.name in config.Prefs.plugins.active_list
            if i.enabled:
                i.event("enable")

    def plugin_list(self):
        return self.plugins

    #Later on, I'm hoping to be able to give the plugin itself a new view/tab
    def new_tab(plugin):
        pass

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
        debug.dprint("PLUGIN: init(); New plugin being made: '%(name)s' in %(path)s" % locals())
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
            debug.dprint("PLUGIN: initialize_plugin; cwd: %s !!!!!!!!!!!!!!!!!" % os.getcwd())
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
            debug.dprint("PLUGIN: initialize_plugin(); Error loading plugin '%s' in %s" % (self.name, self.path))
            self.valid = self.is_installed = False
            return False
        debug.dprint("PLUGIN: initialize_plugin(); !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.event_table = self.module.event_table
        self.desc = self.module.desc
        self.is_installed = self.module.is_installed
        debug.dprint("PLUGIN: %s event_table = %s" %(self.name, str(self.event_table)))
        debug.dprint("PLUGIN: %s desc = %s" %(self.name, str(self.desc)))
        debug.dprint("PLUGIN: %s is_installed = %s" %(self.name, str(self.is_installed)))
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
            debug.dprint("PLUGIN: event(): %s , not defined for plugin: %s" %(event,self.name))
            debug.dprint("PLUGIN: event(): event_table = " + str(self.event_table))
            return a
        if not a:
            debug.dprint("PLUGIN: event: recieved '%s' as response from %s" %(str(a), self.name))
        return a
        #return self.event_table[event](*args)

class PluginGUI(gtk.Window):
    """Class to implement plugin architecture."""

    def __init__(self, plugin_manager):
        """ Initialize Plugins Dialog Window """
        # Preserve passed parameters and manager
        self.plugin_manager = plugin_manager
        self.gladefile = config.Prefs.DATA_PATH + "glade/porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "plugin_dialog", config.Prefs.APP)
        
        # Connect Callbacks
        callbacks = {
            "on_okbutton_clicked": self.destroy_cb,
            "on_plugin_dialog_destroy": self.destroy_cb
        }
        self.wtree.signal_autoconnect(callbacks)
        self.create_plugin_list()

    def add_vbox_widgets(self):
        return_button = gtk.Button("Return")
        return_button.connect("clicked", self.destroy_cb)
        self.vbox.pack_end(return_button, TRUE, TRUE, 0)
        self.textbuffer = gtk.TextBuffer()
        self.textbox = gtk.TextView(self.textbuffer)
        self.vbox.pack_start(self.textbox)

    def create_plugin_list(self):
        """Creates the list-view of the plugins"""
        self.plugin_view = self.wtree.get_widget("plugin_view")
        
        self.liststore = gtk.ListStore(bool, str, bool)
        self.plugin_view.set_model(self.liststore)
        for i in self.plugin_manager.plugin_list(): 
            debug.dprint("PLUGIN: create_plugin_list(): %s , is_installed = %s" %(i.name, str(i.module.is_installed)))
            if not i.module.is_installed:
                i.enabled = False
            self.liststore.append([i.enabled, i.name, i.module.is_installed])
        cb_column = gtk.TreeViewColumn(_("Enable"))
        text_column = gtk.TreeViewColumn(_("Plug-in"))
        installed_column = gtk.TreeViewColumn(_("Installed"))
        
        cell_tg = gtk.CellRendererToggle()
        cell_tx = gtk.CellRendererText()
        cell_in = gtk.CellRendererText()
        cb_column.pack_start(cell_tg)
        text_column.pack_start(cell_tx)
        installed_column.pack_start(cell_in)
        
        self.plugin_view.append_column(cb_column)
        self.plugin_view.append_column(text_column)
        self.plugin_view.append_column(installed_column)
        
        cb_column.add_attribute(cell_tg,"active",0)
        text_column.add_attribute(cell_tx,"text",1)
        installed_column.add_attribute(cell_in,"text",2)
        
        cell_tg.connect("toggled", self.cb_toggled)
        selection = self.plugin_view.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect("changed", self.sel_changed)
        selection.select_iter(self.liststore.get_iter_first())
        selection.emit("changed")

    #Callbacks:
    def cb_toggled( self, widget, *args ):
        """Handles the enabled/disabled checkbox"""
        selection = self.plugin_view.get_selection()
        treemodel, row = selection.get_selected()
        changed_plugin_name = treemodel.get(row, 1)
        if not row:
            return
        changed_plugin = self.plugin_manager.get_plugin(*changed_plugin_name)
        changed_plugin.toggle_enabled()
        treemodel.set(row, 0, changed_plugin.enabled)
        if changed_plugin.enabled:
            if changed_plugin.name not in config.Prefs.plugins.active_list:
                config.Prefs.plugins.active_list.append(changed_plugin.name)
        else:
            if changed_plugin.name in config.Prefs.plugins.active_list:
                index = config.Prefs.plugins.active_list.index(changed_plugin.name)
                config.Prefs.plugins.active_list = config.Prefs.plugins.active_list[:index-1] + config.Prefs.plugins.active_list[index+1:]

    def sel_changed(self, selection, *args):
        treemodel, row = selection.get_selected()
        changed_plugin_name = treemodel.get(row, 1)
        if not row:
            return
        changed_plugin = self.plugin_manager.get_plugin(*changed_plugin_name)
        plugin_desc = self.wtree.get_widget("plugin_desc")
        text_buffer = gtk.TextBuffer()
        text_buffer.set_text(changed_plugin.desc)
        plugin_desc.set_buffer(text_buffer)
        #Load a plugin's option screen here

    def destroy_cb(self, *args):
        window = self.wtree.get_widget("plugin_dialog")
        if window:
            window.destroy()
