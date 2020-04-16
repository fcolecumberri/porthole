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
print("PLUGIN: id initialized to ", id)

import gtk
#import imp
from gettext import gettext as _

#from porthole.utils import utils
from porthole.utils import debug
#from porthole.importer import my_import
from porthole import config


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
        self.vbox.pack_end(return_button, True, True, 0)
        self.textbuffer = gtk.TextBuffer()
        self.textbox = gtk.TextView(self.textbuffer)
        self.vbox.pack_start(self.textbox)

    def create_plugin_list(self):
        """Creates the list-view of the plugins"""
        self.plugin_view = self.wtree.get_widget("plugin_view")

        self.liststore = gtk.ListStore(bool, str, bool)
        self.plugin_view.set_model(self.liststore)
        for i in self.plugin_manager.plugin_list():
            debug.dprint("PLUGIN: create_plugin_list(): plugin_list=" + str(self.plugin_manager.plugin_list()))
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
    def cb_toggled( self, widget, path ):
        """Handles the enabled/disabled checkbox"""
        self.plugin_view.set_cursor(path)
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
