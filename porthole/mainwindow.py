#!/usr/bin/env python

'''
    Porthole Main Window
    The main interface the user will interact with

    Copyright (C) 2003 Fredrik Arnerup and Daniel G. Taylor

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

import threading, re
import pygtk; pygtk.require("2.0") #make sure we have the right version
import gtk, gtk.glade, gobject, pango
import portagelib

from about import AboutDialog
from depends import DependsTree
from utils import load_web_page, get_icon_for_package, is_root, dprint, get_treeview_selection
from process import ProcessWindow
from summary import Summary
from views import CategoryView, PackageView, DependsView

class MainWindow:
    """Main Window class to setup and manage main window interface."""
    
    def __init__(self):
        #setup glade
        self.gladefile = "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "main_window")
        #register callbacks
        callbacks = {
            "on_main_window_destroy" : gtk.mainquit,
            "on_quit1_activate" : gtk.mainquit,
            "on_emerge_package" : self.emerge_package,
            "on_unmerge_package" : self.unmerge_package,
            "on_sync_tree" : self.sync_tree,
            "on_upgrade_packages" : self.upgrade_packages,
            "on_package_search" : self.package_search,
            "on_search_entry_activate": self.package_search,
            "on_help_contents" : self.help_contents,
            "on_about" : self.about,
            "on_category_view_cursor_changed" : self.category_changed,
            "on_package_view_cursor_changed" : self.package_changed,
            "view_filter_changed" : self.view_filter_changed,
            "on_pretend1_activate" : self.pretend_set,
            "on_notebook_switch_page" : self.notebook_changed
            }
        self.wtree.signal_autoconnect(callbacks)
        # aliases for convenience
        self.notebook = self.wtree.get_widget("notebook")
        #set unfinished items to not be sensitive
        self.wtree.get_widget("view_statistics1").set_sensitive(gtk.FALSE)
        self.wtree.get_widget("contents2").set_sensitive(gtk.FALSE)
        # self.wtree.get_widget("btn_help").set_sensitive(gtk.FALSE)
        #set things we can't do unless a package is selected to not sensitive
        self.set_package_actions_sensitive(gtk.FALSE)
        # setup the category view
        self.category_view = CategoryView()
        self.category_view.register_callback(self.category_changed)
        self.wtree.get_widget("category_scrolled_window").add(self.category_view)
        # setup the package treeview
        self.package_view = PackageView()
        self.package_view.register_callbacks(self.package_changed)
        self.wtree.get_widget("package_scrolled_window").add(self.package_view)
        # setup the dependency treeview
        self.deps_view = DependsView()
        self.wtree.get_widget("dependencies_scrolled_window").add(self.deps_view)
        #setup sudo use
        self.use_sudo = -1
        #want to use -p option for pretend?
        self.pretend = ""
        # summary view
        scroller = self.wtree.get_widget("summary_text_scrolled_window");
        self.summary = Summary()
        scroller.add(self.summary)
        self.summary.show()
        #declare the database
        self.db = None
        #move horizontal and vertical panes
        self.wtree.get_widget("hpane").set_position(280)
        self.wtree.get_widget("vpane").set_position(250)
        #load the db
        self.db_thread = portagelib.DatabaseReader()
        self.db_thread.start()
        gtk.timeout_add(100, self.update_db_read)
        #set status
        self.set_statusbar("Reading package database: %i packages read"
                           % 0)

    def check_for_root(self, callback = None):
        """figure out if the user can emerge or not..."""
        if not is_root():
            self.sudo_dialog = gtk.Dialog(
                "You are not root!",
                self.wtree.get_widget("main_window"),
                gtk.DIALOG_MODAL or gtk.DIALOG_DESTROY_WITH_PARENT,
                ("_Yes", 0))
            self.sudo_dialog.add_button("_No", 1)
            sudo_text = gtk.Label("Do you want use the sudo command "
                                  "to install programs?\nNOTE: sudo "
                                  "must be setup correctly!")
            sudo_text.set_padding(5, 5)
            self.sudo_dialog.vbox.pack_start(sudo_text)
            sudo_text.show()
            self.sudo_dialog.connect("response", self.sudo_response)
            self.sudo_dialog.show_all()
        else:
            self.use_sudo = 0
        if callback:
            self.sudo_dialog.callback = callback

    def sudo_response(self, widget, response):
        """Parse response from the user about sudo usage"""
        if response == 0:
            self.use_sudo = 1
        else:
            self.use_sudo = 2
        callback = self.sudo_dialog.callback
        self.sudo_dialog.destroy()
        if callback:
            callback(None)

    def set_statusbar(self, string):
        """Update the statusbar without having to use push and pop."""
        statusbar = self.wtree.get_widget("statusbar1")
        statusbar.pop(0)
        statusbar.push(0, string)

    def update_db_read(self):
        """Update the statusbar according to the number of packages read."""
        if not self.db_thread.done:
            self.set_statusbar("Reading package database: %i packages read"
                               % self.db_thread.count)
        elif self.db_thread.error:
            # todo: display error dialog instead
            self.db_thread.join()
            self.set_statusbar(self.db_thread.error.decode('ascii', 'replace'))
            return gtk.FALSE  # disconnect from timeout
        else:
            self.db = self.db_thread.get_db()
            self.set_statusbar("Populating tree ...")
            self.db_thread.join()
            self.category_view.populate(self.db.categories.keys())
            self.update_statusbar(self.SHOW_ALL)
            self.wtree.get_widget("menubar").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("toolbar").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("view_filter").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("search_entry").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("btn_search").set_sensitive(gtk.TRUE)
            return gtk.FALSE  # disconnect from timeout
        return gtk.TRUE

    def setup_command(self, command, callback = None):
        """Setup the command to run with sudo or not at all"""
        env = {"FEATURES": "notitles"}  # Don't try to set the titlebar
        if self.use_sudo == -1 and not self.pretend:
            self.check_for_root(callback)
        else:
            if self.use_sudo:
                if self.use_sudo == 1:
                    ProcessWindow("sudo " + command, env)
                elif self.pretend and command != "emerge sync":
                    ProcessWindow(command, env)
                else:
                    print "Sorry, can't do that!"
            else:
                ProcessWindow(command, env)

    def pretend_set(self, widget):
        """Set whether or not we are going to use the --pretend flag"""
        if widget.get_active():
            self.pretend = "--pretend "
        else:
            self.pretend = ""

    def emerge_package(self, widget):
        """Emerge the currently selected package."""
        package = get_treeview_selection(
            self.package_view, 2)
        command = self.setup_command("emerge " + self.pretend
            + package.get_category() + "/" +
            package.get_name(), self.emerge_package)

    def unmerge_package(self, widget):
        """Unmerge the currently selected package."""
        package = get_treeview_selection(
            self.package_view, 2)
        command = self.setup_command("emerge unmerge " +
            self.pretend + package.get_category() + "/" +
            package.get_name(), self.unmerge_package)

    def sync_tree(self, widget):
        """Sync the portage tree and reload it when done."""
        command = self.setup_command("emerge sync", self.sync_tree)

    def upgrade_packages(self, widget):
        """Upgrade all packages that have newer versions available."""
        command = self.setup_command("emerge -uD " + self.pretend +
                                     "world", self.upgrade_packages)

    def package_search(self, widget):
        """Search package db with a string and display results."""
        search_term = self.wtree.get_widget("search_entry").get_text()
        if search_term:
            search_results = self.package_view.search_model
            search_results.clear()
            re_object = re.compile(search_term, re.I)
            count = 0
            search_desc = self.wtree.get_widget("search_descriptions1").get_active()
            # no need to sort self.db.list; it is already sorted
            for name, data in self.db.list:
                searchstring = name
                if search_desc:
                    desc = data.get_properties().description
                    searchstring += desc
                if re_object.search(searchstring):
                    count += 1
                    iter = search_results.insert_before(None, None)
                    search_results.set_value(iter, 0, name)
                    search_results.set_value(iter, 2, data)
                    #set the icon depending on the status of the package
                    icon = get_icon_for_package(data)
                    view = self.package_view
                    search_results.set_value(
                        iter, 1,
                        view.render_icon(icon,
                                         size = gtk.ICON_SIZE_MENU,
                                         detail = None))
            search_results.size = count  # store number of matches
            self.wtree.get_widget("view_filter").set_history(self.SHOW_SEARCH)
            # in case the search view was already active
            self.update_statusbar(self.SHOW_SEARCH)
                
    def help_contents(self, widget):
        """Show the help file contents."""
        pass

    def about(self, widget):
        """Show about dialog."""
        dialog = AboutDialog()

    def category_changed(self, category):
        """Catch when the user changes categories."""
        mode = self.wtree.get_widget("view_filter").get_history()
        if not category:
            packages = None
        elif mode == self.SHOW_ALL:
            packages = self.db.categories[category]
        elif mode == self.SHOW_INSTALLED:
            packages = self.db.installed[category]
        else:
            raise Exception("The programmer is stupid.");
        self.package_view.populate(packages)
        self.summary.update_package_info(None)
        self.set_package_actions_sensitive(gtk.FALSE)

    def package_changed(self, package):
        """Catch when the user changes packages."""
        self.summary.update_package_info(package)
        #if the user is looking at the deps we need to update them
        notebook = self.wtree.get_widget("notebook")
        if notebook.get_current_page() == 1:
            self.deps_view.fill_depends_tree(self.deps_view, package)
        self.set_package_actions_sensitive(gtk.TRUE)

    def notebook_changed(self, widget, pointer, index):
        """Catch when the user changes the notebook"""
        if index == 1:
            #fill the deps view!
            package = get_treeview_selection(self.package_view, 2)
            self.deps_view.fill_depends_tree(self.deps_view, package)

    SHOW_ALL = 0
    SHOW_INSTALLED = 1
    SHOW_SEARCH = 2
    SHOW_UPGRADE = 3
    def view_filter_changed(self, widget):
        """Update the treeviews for the selected filter"""
        index = widget.get_history()
        self.update_statusbar(index)
        cat_scroll = self.wtree.get_widget("category_scrolled_window")
        if index in (self.SHOW_INSTALLED, self.SHOW_ALL):
            cat_scroll.show();
            self.populate_category_tree(
                index == self.SHOW_ALL
                and self.db.categories.keys()
                or self.db.installed.keys())
            self.package_view.set_view(self.package_view.PACKAGES)
            self.package_view.clear()
            self.summary.update_package_info(None)
        elif index == self.SHOW_SEARCH:
            cat_scroll.hide();
            self.package_view.set_view(self.package_view.SEARCH_RESULTS)
        elif index == self.SHOW_UPGRADE:
            cat_scroll.hide();
            self.fill_upgrade_results()
            self.package_view.set_view(self.package_view.UPGRADABLE)
        self.set_package_actions_sensitive(gtk.FALSE)
        self.deps_view.clear()

    def fill_upgrade_results(self):
        """fill upgrade tree"""
        upgrade_results = self.package_view.upgrade_model
        upgrade_results.clear()
        installed = []
        for cat, packages in self.db.installed.items():
            for name, package in packages.items():
                if package.upgradable():
                    installed += [(package.full_name, package)]
        installed = portagelib.sort(installed)
        world = open("/var/cache/edb/world", "r").read().split()
        for full_name, package in installed:
            iter = upgrade_results.insert_before(None, None)
            upgrade_results.set_value(iter, 0, full_name)
            upgrade_results.set_value(iter, 2, package)
            upgrade_results.set_value(iter, 1,
                                      full_name in world
                                      and gtk.TRUE or gtk.FALSE)
        return

    def update_statusbar(self, mode):
        """Update the statusbar for the selected filter"""
        text = "(undefined)"
        if mode == self.SHOW_ALL:
            text = "%d packages in %d categories" % (len(self.db.list),
                                                     len(self.db.categories))
        elif mode == self.SHOW_INSTALLED:
            text = "%d packages in %d categories" % (self.db.installed_count,
                                                     len(self.db.installed))
        elif mode == self.SHOW_SEARCH:
            text = "%d matches found" % self.package_view.search_model.size
        self.set_statusbar(text)

    def set_package_actions_sensitive(self, enabled):
        """Sets package action buttons/menu items to sensitive or not"""
        self.wtree.get_widget("emerge_package1").set_sensitive(enabled)
        self.wtree.get_widget("unmerge_package1").set_sensitive(enabled)
        self.wtree.get_widget("btn_emerge").set_sensitive(enabled)
        self.wtree.get_widget("btn_unmerge").set_sensitive(enabled)
        self.notebook.set_sensitive(enabled)
