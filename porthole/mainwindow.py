#!/usr/bin/env python

'''
    Porthole Main Window
    The main interface the user will interact with

    Copyright (C) 2003 - 2004 Fredrik Arnerup and Daniel G. Taylor

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
import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, gtk.glade, gobject, pango
import portagelib

from about import AboutDialog
from depends import DependsTree
from utils import load_web_page, get_icon_for_package, is_root, dprint, \
     get_treeview_selection, YesNoDialog, SingleButtonDialog
from process import ProcessWindow
from summary import Summary
from views import CategoryView, PackageView, DependsView

class MainWindow:
    """Main Window class to setup and manage main window interface."""
    def __init__(self, preferences = None):
        # setup prefs
        self.prefs = preferences
        # setup glade
        self.gladefile = "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "main_window")
        # register callbacks
        callbacks = {
            "on_main_window_destroy" : gtk.mainquit,
            "on_main_window_size_request" : self.size_update,
            "on_quit1_activate" : gtk.mainquit,
            "on_emerge_package" : self.emerge_package,
            "on_unmerge_package" : self.unmerge_package,
            "on_sync_tree" : self.sync_tree,
            "on_upgrade_packages" : self.upgrade_packages,
            "on_package_search" : self.package_search,
            "on_search_entry_activate": self.package_search,
            "on_help_contents" : self.help_contents,
            "on_about" : self.about,
            "view_filter_changed" : self.view_filter_changed,
            "on_pretend1_activate" : self.pretend_set,
            "on_notebook_switch_page" : self.notebook_changed,
            "on_fetch_activate" : self.fetch_set,
            "on_verbose_activate" : self.verbose_set
            }
        self.wtree.signal_autoconnect(callbacks)
        # aliases for convenience
        self.notebook = self.wtree.get_widget("notebook")
        # set unfinished items to not be sensitive
        self.wtree.get_widget("view_statistics1").set_sensitive(gtk.FALSE)
        self.wtree.get_widget("contents2").set_sensitive(gtk.FALSE)
        # self.wtree.get_widget("btn_help").set_sensitive(gtk.FALSE)
        # setup the category view
        self.category_view = CategoryView()
        self.category_view.register_callback(self.category_changed)
        self.wtree.get_widget(
            "category_scrolled_window").add(self.category_view)
        # setup the package treeview
        self.package_view = PackageView()
        self.package_view.register_callbacks(self.package_changed)
        self.wtree.get_widget("package_scrolled_window").add(self.package_view)
        # setup the dependency treeview
        self.deps_view = DependsView()
        self.wtree.get_widget(
            "dependencies_scrolled_window").add(self.deps_view)
        # summary view
        scroller = self.wtree.get_widget("summary_text_scrolled_window");
        self.summary = Summary()
        scroller.add(self.summary)
        self.summary.show()
        # move horizontal and vertical panes
        self.wtree.get_widget("hpane").set_position(self.prefs.main.hpane)
        self.wtree.get_widget("vpane").set_position(self.prefs.main.vpane)
        # how should we setup our saved menus?
        if self.prefs.emerge.pretend:
            self.wtree.get_widget("pretend1").set_active(gtk.TRUE)
        if self.prefs.emerge.fetch:
            self.wtree.get_widget("fetch").set_active(gtk.TRUE)
        if self.prefs.emerge.verbose:
            self.wtree.get_widget("verbose4").set_active(gtk.TRUE)
        # restore last window width/height
        self.wtree.get_widget("main_window").resize(self.prefs.main.width,
                                                    self.prefs.main.height)
        # initialize our data
        self.init_data()
        # let the user know if he can emerge or not
        self.check_for_root()

    def init_data(self):
        # set things we can't do unless a package is selected to not sensitive
        self.set_package_actions_sensitive(gtk.FALSE)
        self.category_view.clear()  # clear just in case it's populated
        # clear search results
        if self.wtree.get_widget("view_filter").get_history() != self.SHOW_SEARCH:
            self.package_view.clear()
        # upgrades loaded?
        self.upgrades_loaded = False
        # upgrade loading callback
        self.upgrades_loaded_callback = None
        # declare the database
        self.db = None
        # load the db
        self.db_thread = portagelib.DatabaseReader()
        self.db_thread.start()
        gtk.timeout_add(100, self.update_db_read)
        # set status
        self.set_statusbar("Reading package database: %i packages read"
                           % 0)

    def check_for_root(self):
        """figure out if the user can emerge or not..."""
        self.is_root = is_root()
        if not self.is_root:
            self.no_root_dialog = SingleButtonDialog("You are not root!",
                            self.wtree.get_widget("main_window"),
                            "You will not be able to emerge, unmerge,"
                            " upgrade or sync!", self.no_root_response,
                            "_Ok")

    def no_root_response(self, widget, response):
        """ Remove the dialog when Ok is pressed """
        dprint("Accepted no_root, removing dialog")
        self.no_root_dialog.destroy()

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
            # make sure we search again if we reloaded!
            view_filter = self.wtree.get_widget("view_filter")
            if view_filter.get_history() == self.SHOW_SEARCH:
                self.package_view.size = 0
                self.package_search(None)
            # update the views by calling view_filter_changed
            self.view_filter_changed(view_filter)
            return gtk.FALSE  # disconnect from timeout
        return gtk.TRUE

    def setup_command(self, command):
        """Setup the command to run or not"""
        env = {"FEATURES": "notitles"}  # Don't try to set the titlebar
        if self.is_root or (self.prefs.emerge.pretend and
                            command[:11] != "emerge sync"):
            if self.prefs.emerge.pretend:
                callback = None
            else:
                callback = self.init_data
            ProcessWindow(command, env, self.prefs, callback)
        else:
            dprint("Sorry, you aren't root! -> " + command)
            self.sorry_dialog = SingleButtonDialog("You are not root!",
                    self.wtree.get_widget("main_window"),
                    "Please run Porthole as root to emerge packages!",
                    self.sorry_dialog_response, "_Ok")

    def sorry_dialog_response(self, widget, response):
        """ Removes sorry dialog when Ok is pressed """
        self.sorry_dialog.destroy()

    def pretend_set(self, widget):
        """Set whether or not we are going to use the --pretend flag"""
        self.prefs.emerge.pretend = widget.get_active()

    def fetch_set(self, widget):
        """Set whether or not we are going to use the --fetchonly flag"""
        self.prefs.emerge.fetch = widget.get_active()

    def verbose_set(self, widget):
        """Set whether or not we are going to use the --verbose flag"""
        self.prefs.emerge.verbose = widget.get_active()

    def emerge_package(self, widget):
        """Emerge the currently selected package."""
        package = get_treeview_selection(self.package_view, 2)
        self.setup_command("emerge" + self.prefs.emerge.get_string()
                           + package.full_name)

    def unmerge_package(self, widget):
        """Unmerge the currently selected package."""
        package = get_treeview_selection(self.package_view, 2)
        self.setup_command("emerge unmerge" +
                self.prefs.emerge.get_string() + package.full_name)

    def sync_tree(self, widget):
        """Sync the portage tree and reload it when done."""
        sync = "emerge sync"
        if self.prefs.emerge.verbose:
            sync += " --verbose"
        self.setup_command(sync)

    def upgrade_packages(self, widget):
        """Upgrade selected packages that have newer versions available."""
        if self.upgrades_loaded:
            # create a list of packages to be upgraded
            packages_list = ""
            model = self.package_view.upgrade_model
            iter = model.get_iter_first()
            while(iter):
                # upgrade only if it's checked!
                if model.get_value(iter, 1):
                    packages_list += model.get_value(iter, 0) + " "
                # step to next iter
                iter = model.iter_next(iter)
            dprint("Updating packages...")
            self.setup_command("emerge -u" + self.prefs.emerge.get_string() +
                               packages_list)
        else:
            dprint("Upgrades not loaded; upgrade world?")
            self.upgrades_loaded_dialog = YesNoDialog("Upgrade requested",
                    self.wtree.get_widget("main_window"),
                    "Do you want to upgrade all packages in your world file?",
                     self.upgrades_loaded_dialog_response)

    def upgrades_loaded_dialog_response(self, widget, response):
        """ Get and parse user's response """
        if response == 0: # Yes was selected
            self.load_upgrades_list()
            self.upgrades_loaded_callback = self.upgrade_packages
        # get rid of the dialog
        self.upgrades_loaded_dialog.destroy()

    def package_search(self, widget):
        """Search package db with a string and display results."""
        search_term = self.wtree.get_widget("search_entry").get_text()
        if search_term:
            search_results = self.package_view.search_model
            search_results.clear()
            re_object = re.compile(search_term, re.I)
            count = 0
            search_desc = self.wtree.get_widget(
                "search_descriptions1").get_active()
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
                    # set the icon depending on the status of the package
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
        self.deps_view.clear()

    def package_changed(self, package):
        """Catch when the user changes packages."""
        self.summary.update_package_info(package)
        # if the user is looking at the deps we need to update them
        notebook = self.wtree.get_widget("notebook")
        if notebook.get_current_page() == 1:
            self.deps_view.fill_depends_tree(self.deps_view, package)
        self.set_package_actions_sensitive(gtk.TRUE)

    def notebook_changed(self, widget, pointer, index):
        """Catch when the user changes the notebook"""
        if index == 1:
            # fill the deps view!
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
            self.category_view.populate(
                index == self.SHOW_ALL
                and self.db.categories.keys()
                or self.db.installed.keys())
            self.package_view.set_view(self.package_view.PACKAGES)
            self.package_view.clear()
            self.summary.update_package_info(None)
        elif index == self.SHOW_SEARCH:
            cat_scroll.hide();
            dprint("Showing search results")
            self.package_view.set_view(self.package_view.SEARCH_RESULTS)
        elif index == self.SHOW_UPGRADE:
            if not self.upgrades_loaded:
                self.load_upgrades_list()
            else:
                # already loaded, just show them!
                cat_scroll.hide();
                self.package_view.set_view(self.package_view.UPGRADABLE)
                self.summary.update_package_info(None)
        self.set_package_actions_sensitive(gtk.FALSE)
        self.deps_view.clear()

    def load_upgrades_list(self):
        # upgrades are not loaded, create dialog and load them
        self.wait_dialog = SingleButtonDialog("Please Wait!",
                self.wtree.get_widget("main_window"),
                "Loading upgradable packages list...",
                self.wait_dialog_response, "_Cancel")
        # create upgrade thread for loading the upgrades
        self.ut = UpgradableReader(self.package_view.upgrade_model,
                                   self.db.installed.items())
        self.ut.start()
        # add a timeout to check if thread is done
        gtk.timeout_add(100, self.update_upgrade_thread)

    def wait_dialog_response(self, widget, response):
        """ Get a response from the wait dialog """
        if response == 0:
            # terminate the thread
            self.ut.please_die()
            self.ut.join()
            # get rid of the dialog
            self.wait_dialog.destroy()

    def update_upgrade_thread(self):
        """ Find out if thread is finished """
        # needs error checking perhaps...
        if self.ut.done:
            if self.ut.cancelled:
                return gtk.FALSE
            self.ut.join()
            self.wait_dialog.destroy()
            self.upgrades_loaded = True
            if self.upgrades_loaded_callback:
                self.upgrades_loaded_callback(None)
                self.upgrades_loaded_callback = None
            else:
                self.package_view.set_view(self.package_view.UPGRADABLE)
                self.summary.update_package_info(None)
                self.wtree.get_widget("category_scrolled_window").hide()
            return gtk.FALSE
        return gtk.TRUE

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

    def size_update(self, widget, gbox):
        """ Store the window and pane positions """
        pos = widget.get_size()
        self.prefs.main.x = pos[0]
        self.prefs.main.y = pos[1]
        self.prefs.main.hpane = self.wtree.get_widget("hpane").get_position()
        self.prefs.main.vpane = self.wtree.get_widget("vpane").get_position()



class UpgradableReader(threading.Thread):
    """ Read available upgrades and store them in a treemodel """
    def __init__(self, upgrade_model, installed):
        """ Initialize """
        threading.Thread.__init__(self)
        self.upgrade_results = upgrade_model
        self.installed_items = installed
        self.done = False
        self.cancelled = False
        # quit even if this thread is still running
        self.setDaemon(1)
    
    def run(self):
        """fill upgrade tree"""
        self.upgrade_results.clear()    # clear the treemodel
        installed = []
        # find upgradable packages
        for cat, packages in self.installed_items:
            for name, package in packages.items():
                if self.cancelled: self.done = True; return
                if package.upgradable():
                    installed += [(package.full_name, package)]
        installed = portagelib.sort(installed)
        # read system world file
        # using this file, only packages explicitly installed by
        # the user are upgraded by default
        world = open("/var/cache/edb/world", "r").read().split()
        # add the packages to the treemodel
        for full_name, package in installed:
            iter = self.upgrade_results.insert_before(None, None)
            self.upgrade_results.set_value(iter, 0, full_name)
            self.upgrade_results.set_value(iter, 2, package)
            self.upgrade_results.set_value(iter, 1,
                                           full_name in world
                                           and gtk.TRUE or gtk.FALSE)
        # set the thread as finished
        self.done = True

    def please_die(self):
        self.cancelled = True
