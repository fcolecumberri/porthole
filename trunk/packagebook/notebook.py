#!/usr/bin/env python
# -*- coding: UTF8 -*-

'''
    Porthole Main Window
    The main interface the user will interact with

    Copyright (C) 2003 - 2006    Fredrik Arnerup, Brian Dolbec, 
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

import threading, re #, types
import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, gtk.glade, gobject, pango
import os, sys
from gettext import gettext as _

import utils.debug

import backends
portage_lib = backends.portage_lib

World = portage_lib.World

import config
from utils.dispatcher import Dispatcher
from summary import Summary
from views.depends import DependsView
from views.commontreeview import CommonTreeView
from depends import DependsTree
from plugin import PluginGUI, PluginManager
from loaders.loaders import *
from backends.version_sort import ver_match
#from timeit import Timer


ON = True
OFF = False


class PackageNotebook:
    """Contains all functions for managing a packages detailed views"""

    def __init__( self,  wtree, callbacks, plugin_package_tabs):
        self.wtree = wtree
        self.callbacks = callbacks
        self.plugin_package_tabs = plugin_package_tabs
        self.notebook = self.wtree.get_widget("notebook")
        self.installed_window = self.wtree.get_widget("installed_files_scrolled_window")
        self.changelog = self.wtree.get_widget("changelog").get_buffer()
        self.installed_files = self.wtree.get_widget("installed_files").get_buffer()
        self.ebuild = self.wtree.get_widget("ebuild").get_buffer()
        # summary view
        scroller = self.wtree.get_widget("summary_text_scrolled_window");
        self.summary = Summary(Dispatcher(self.callbacks["summary_callback"]), self.callbacks["re_init_portage"])
        result = scroller.add(self.summary)
        self.summary.show()
        # setup the dependency treeview
        self.deps_view = DependsView(self.new_notebook)
        self.deps_filled = False
        self.deps_version = ""

        result = self.wtree.get_widget("dependencies_scrolled_window").add(self.deps_view)
        self.notebook.connect("switch-page", self.notebook_changed)
        self.reset_tabs()
        
    def set_package(self, package):
        """sets the package for all dispalys"""
        self.package = package
        self.reset_tabs()
        self.summary.update_package_info(package)
        self.notebook_changed(None, None, self.notebook.get_current_page())

    def reset_tabs(self):
        """set notebook tabs to load new package info"""
        self.deps_filled = self.changelog_loaded = self.installed_loaded = self.ebuild_loaded = False
        self.ebuild_loaded_version = None

    def notebook_changed(self, widget, pointer, index):
        """Catch when the user changes the notebook"""
        package = self.package
        utils.debug.dprint("NOTEBOOK: notebook_changed(); self.summary.ebuild " +self.summary.ebuild + " self.deps_version : " + self.deps_version)
        if index == 1:
            if  self.deps_version != self.summary.ebuild or not self.deps_filled:
                utils.debug.dprint("NOTEBOOK: notebook_changed(); fill the deps view!")
                self.deps_view.fill_depends_tree(self.deps_view, package, self.summary.ebuild)
                self.deps_filled = True
                self.deps_version = self.summary.ebuild
        elif index == 2:
            if not self.changelog_loaded:
                # fill in the change log
                load_textfile(self.changelog, package, "changelog")
                self.changelog_loaded = True
        elif index == 3:
            if not self.installed_loaded:
                # load list of installed files
                load_installed_files(self.installed_window, self.installed_files, package)
                self.installed_loaded = True
        elif index == 4:
            utils.debug.dprint("MAINWINDOW: notebook_changed(); self.summary.ebuild = " + str(self.summary.ebuild))
            if not self.ebuild_loaded or self.ebuild_loaded_version != self.summary.ebuild:
                #load_textfile(self.ebuild, package, "best_ebuild")
                load_textfile(self.ebuild, package, "version_ebuild", self.summary.ebuild)
                self.ebuild_loaded = True
                self.ebuild_loaded_version = self.summary.ebuild
        else:
            for i in self.plugin_package_tabs:
                #Search through the plugins dictionary and select the correct one.
                if self.plugin_package_tabs[i][2] == index:
                    self.plugin_package_tabs[i][0]( package )

    def clear_notebook(self):
        """ Clear all notebook tabs & disable them """
        #utils.debug.dprint("MAINWINDOW: clear_notebook()")
        self.summary.update_package_info(None)
        self.deps_view.clear()
        self.changelog.set_text('')
        self.installed_files.set_text('')
        self.ebuild.set_text('')

    def new_notebook(self, package):
        """creates a new popup window containing a new notebook instance
        to display 'package'"""
        if not self.dep_window:
            self.dep_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.dep_notebook = PackageNotebook(self.wtree, self.callbacks, self.plugin_package_tabs)
            self.dep_window.add(self.dep_notebook)
            #self.dep_window.connect("destroy", gtk.main_quit)
            self.dep_window.resize(600, 400)
            self.dep_window.set_title(_("Porthole Dependency Viewer")) 
            self.dep_window.show_all()
        return self.dep_window, self.dep_notebook
        
        
        
        
