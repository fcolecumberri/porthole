#!/usr/bin/env python

'''
    Porthole Mainwindow statusbar support
    Support class and functions for the mainwindow interface

    Copyright (C) 2003 - 2011
    Fredrik Arnerup, Brian Dolbec,
    Daniel G. Taylor, Wm. F. Wheeler, Tommy Iorns

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


from gi.repository import Gtk
from gettext import gettext as _

from porthole import config
from porthole.utils import debug
from porthole.mwsupport.pluginmanager import PluginManager
from porthole.mwsupport.plugingui import PluginGUI
from porthole.mwsupport.action import ActionHandler


class PluginHandler(ActionHandler):
    '''Support functions for plugins'''

    def __init__(self):
        """basic init"""
        ActionHandler.__init__(self)
        self.needs_plugin_menu = False
        self.plugin_root_menu = None
        self.plugin_menu = None
        self.plugin_manager = None
        # initialize this now cause we need it next
        self.plugin_package_tabs = {}
        self.plugin_views = {}
        self.status = None

    def setup_plugins(self):
        """set up our plug-in manager and variables"""
        #Plugin-related statements
        self.needs_plugin_menu = False
        #debug.dprint("PluginHandler; setup_plugins(): path_list %s"
                #% config.Prefs.plugins.path_list)
        debug.dprint("PluginHandler: setup_plugins: plugin path: %s"
                % config.Prefs.PLUGIN_DIR)
        self.plugin_root_menu = Gtk.MenuItem(_("Active Plugins"))
        self.plugin_menu = Gtk.Menu()
        self.plugin_root_menu.set_submenu(self.plugin_menu)
        self.wtree.get_widget("menubar").append(self.plugin_root_menu)
        self.plugin_manager = PluginManager(self)
        self.plugin_package_tabs = {}
        self.packagebook = None

    def new_plugin_package_tab( self, name, callbacks ):
        """adds a pckagebook notebook page to the notebook"""
        notebook = self.packagebook.notebook
        label = Gtk.Label(label=name)
        notebook.append_page(widget, label)
        page_num = notebook.page_num(widget)
        self.plugin_package_tabs[name] = [callback, label, page_num]

    def del_plugin_package_tab( self, name ):
        """removes a packagenotebook page from the notebook"""
        notebook = self.packagebook.notebook
        notebook.remove_page(self.plugin_package_tabs[name][1])
        self.plugin_package_tabs.pop(name)

    def new_plugin_view( self, name, callbacks, widget ):
        """adds a view menu option to the mainwindow
        @param name: string
        @param name: the name of the view menu option
        @param callbacks: dict
        @param callbacks: {
            "view_changed":None,
            "category_changed": None,
            "package_changed": None,
            "status_update": None,
            "set_pkg_actions": None
            }
        """
        """adds a view menu option to the mainwindow"""
        self.widget["view_filter_list"].append([name])
        self.plugin_views[name] = callbacks
        return (self.category_view, self.package_view, self.packagebook)

    def del_plugin_view( self, name ):
        """removes a view menu option from the mainwindow"""
        self.widget["view_filter_list"].remove([name])
        self.plugin_views.pop(name)


    def plugin_settings_activate( self, widget ):
        """Shows the plugin settings window"""
        self.plugin_dialog = PluginGUI(self.plugin_manager )

    def new_plugin_menuitem( self, label ):
        """adds a menu item for a plugin"""
        debug.dprint("PluginHandler: Adding new Menu Entry")
        if self.needs_plugin_menu == False:
            #Creates plugin Menu
            debug.dprint("PluginHandler: Enabling Plugin Menu")
            self.plugin_root_menu.show()
            self.needs_plugin_menu = True
        new_item = Gtk.MenuItem( label )
        new_item.show()
        self.plugin_menu.append( new_item )
        return new_item

    def del_plugin_menuitem( self, menuitem ):
        """just like the method name says"""
        self.plugin_menu.remove( menuitem )
        if len(self.plugin_menu.get_children()) == 0:
            self.plugin_root_menu.hide()
            self.needs_plugin_menu = False
        del menuitem


