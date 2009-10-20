#!/usr/bin/env python

'''
    Porthole Main Window
    The main interface the user will interact with

    Copyright (C) 2003 - 2008   Fredrik Arnerup, Brian Dolbec, 
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

from porthole.utils import debug
from porthole import backends
portage_lib = backends.portage_lib
#World = portage_lib.settings.get_world()
from porthole import config
from porthole.utils.dispatcher import Dispatcher
from porthole.packagebook.summary import Summary
from porthole.views.depends import DependsView
from porthole.views.commontreeview import CommonTreeView
from porthole.packagebook.depends import DependsTree
from porthole.plugin import PluginGUI, PluginManager
from porthole.loaders.loaders import *
from porthole.backends.version_sort import ver_match
#from timeit import Timer


ON = True
OFF = False


class PackageNotebook:
    """Contains all functions for managing a packages detailed views"""

    def __init__( self,  wtree, callbacks, plugin_package_tabs, parent_name = '', parent_tree = []):
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
        self.summary = Summary(Dispatcher(self.callbacks["action_callback"]), self.callbacks["re_init_portage"])
        result = scroller.add(self.summary)
        self.summary.show()
        # setup the dependency treeview
        self.deps_view = DependsView(self.new_notebook, parent_name, parent_tree, Dispatcher(self.callbacks["action_callback"]))
        self.dep_window = {'window': None, 'notebook': None, 'callback': None, 'label': None, 'tooltip': None, 'tree': '', 'depth': 0}
        result = self.wtree.get_widget("dependencies_scrolled_window").add(self.deps_view)
        self.notebook.connect("switch-page", self.notebook_changed)
        self.reset_tabs()
        
    def set_package(self, package):
        """sets the package for all dispalys"""
        self.package = package
        self.reset_tabs()
        self.summary.update_package_info(package)
        self.notebook_changed(None, None, self.notebook.get_current_page())
        if self.dep_window["window"] != None and self.dep_window["notebook"] != None:
            self.dep_window["notebook"].set_new_parent(package.full_name)

    def reset_tabs(self):
        """set notebook tabs to load new package info"""
        self.loaded = {"deps": False, "changelog": False, "installed": False, "ebuild": False}
        self.loaded_version= {"ebuild" : None, "installed": None, "deps": None}

    def notebook_changed(self, widget, pointer, index):
        """Catch when the user changes the notebook"""
        package = self.package
        debug.dprint("PackageNotebook notebook_changed(); self.summary.ebuild " +self.summary.ebuild +
                                    " self.loaded_version['deps'] : " + str(self.loaded_version["deps"]))
        if index == 1:
            if  self.loaded_version["deps"] != self.summary.ebuild or not self.loaded["deps"]:
                debug.dprint("PackageNotebook notebook_changed(); fill the deps view!")
                self.deps_view.fill_depends_tree(self.deps_view, package, self.summary.ebuild)
                self.loaded["deps"] = True
                self.loaded_version["deps"] = self.summary.ebuild
        elif index == 2:
            if not self.loaded["changelog"]:
                # fill in the change log
                load_textfile(self.changelog, package, "changelog")
                self.loaded["changelog"] = True
        elif index == 3:
            debug.dprint("PackageNotebook notebook_changed(); load installed files for: " + str(self.summary.ebuild))
            if not self.loaded["installed"] or self.loaded_version["installed"] != self.summary.ebuild:
                # load list of installed files
                load_installed_files(self.installed_window, self.installed_files, package, self.summary.ebuild )
                self.loaded["installed"] = True
                self.loaded_version["installed"] = self.summary.ebuild
        elif index == 4:
            debug.dprint("PackageNotebook notebook_changed(); self.summary.ebuild = " + str(self.summary.ebuild))
            if not self.loaded["ebuild"] or self.loaded_version["ebuild"] != self.summary.ebuild:
                #load_textfile(self.ebuild, package, "best_ebuild")
                load_textfile(self.ebuild, package, "version_ebuild", self.summary.ebuild)
                self.loaded["ebuild"] = True
                self.loaded_version["ebuild"] = self.summary.ebuild
        else:
            for i in self.plugin_package_tabs:
                #Search through the plugins dictionary and select the correct one.
                if self.plugin_package_tabs[i][2] == index:
                    self.plugin_package_tabs[i][0]( package )

    def clear_notebook(self):
        """ Clear all notebook tabs & disable them """
        debug.dprint("PackageNotebook clear_notebook()")
        self.summary.update_package_info(None)
        self.deps_view.clear()
        self.changelog.set_text('')
        self.installed_files.set_text('')
        self.ebuild.set_text('')

    def new_notebook(self, callback, parent_name, parent_tree): #, package):
        """creates a new popup window containing a new notebook instance
        to display 'package'"""
        self.dep_window["callback"] = callback
        self.dep_window["tree"] = parent_tree
        self.dep_window['name'] = parent_name
        if not self.dep_window["window"]:
            self.dep_window['window'] = gtk.Window(gtk.WINDOW_TOPLEVEL)
            #self.dep_window['depth'] += 1 # increase the depth number since it is a new window
            v_box = gtk.VBox()
            h_box = gtk.HBox()
            label1 = gtk.Label(_("Viewing Dependency of: "))
            h_box.pack_start(label1, False, False, 0)
            self.dep_window['label'] = gtk.Label()
            h_box.pack_start(self.dep_window['label'], expand=False, fill=False)
            label2 = gtk.Label('')
            h_box.pack_start(label2, expand=True, fill=True)
            v_box.pack_start(h_box, False, False,3)
            self.dep_window['label'].set_has_tooltip(True)
            self.dep_window['label'].set_tooltip_text('')
            gladefile = config.Prefs.DATA_PATH + config.Prefs.use_gladefile
            self.deptree = gtk.glade.XML(gladefile, "notebook", config.Prefs.APP)
            self.dep_window["notebook"] = PackageNotebook(self.deptree, self.callbacks, self.plugin_package_tabs, parent_name, parent_tree[:])
            v_box.pack_start(self.dep_window["notebook"].notebook)
            self.dep_window["window"].add(v_box)
            self.dep_window["window"].connect("destroy", self.close_window)
            self.dep_window["window"].resize(600, 400)
            self.dep_window["window"].show_all()
            debug.dprint("********** PackageNotebook: new_notebook(); DependsView: do_dep_window() new dep_window{'window', 'notebook', 'depth'}" + \
                                    str(self.dep_window["window"]) +str(self.dep_window["notebook"])) # +str(self.dep_window['depth']))
        return self.dep_window
        
    def close_window(self, *widget):
        # first check for and close any children
        if self.dep_window["window"] != None and self.dep_window["notebook"] != None:
            self.dep_window["notebook"].close_window()
        if self.dep_window["window"]:
            self.dep_window["window"].destroy()
            del self.dep_window["window"], self.dep_window["notebook"]
            self.dep_window["window"] = None
            self.dep_window["notebook"] = None
            # tell the initiator that it is destroyed
            if self.dep_window["callback"]:
                self.dep_window["callback"]()
                self.dep_window["callback"] = None
            self.dep_window['tree'] = None

    def set_new_parent(self, name):
        if self.dep_window["notebook"] != None:
            self.dep_window["notebook"].set_new_parent(package.full_name)
            self.dep_window["notebook"].notebook.set_sensitive(False)
            self.dep_window["tree"] = self.dep_window["tree"][:-1]
            self.dep_window.deps_view.parent_tree = self.dep_window.deps_view.parent_tree[:-1]
            self.dep_window.deps_view.set_label(name)


