#!/usr/bin/env python

'''
    Porthole Main Window
    The main interface the user will interact with

    Copyright (C) 2003 - 2004 Fredrik Arnerup, Brian Dolbec, 
    Daniel G. Taylor and Wm. F. Wheeler

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
import portagelib, os, string

from about import AboutDialog
from utils import load_web_page, get_icon_for_package, is_root, dprint, \
     get_treeview_selection, YesNoDialog, SingleButtonDialog, environment
#from process import ProcessWindow
from summary import Summary
from terminal import ProcessManager
from views import CategoryView, PackageView, DependsView
from command import RunDialog
from advemerge import AdvancedEmergeDialog

EXCEPTION_LIST = ['.','^','$','*','+','?','(',')','\\','[',']','|','{','}']

class MainWindow:
    """Main Window class to setup and manage main window interface."""
    def __init__(self, preferences = None, config = None):
        # setup prefs
        self.prefs = preferences
        self.config = config
        # setup glade
        self.gladefile = self.prefs.DATA_PATH + "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "main_window")
        # register callbacks
        callbacks = {
            "on_main_window_destroy" : gtk.mainquit,
            "on_quit1_activate" : gtk.mainquit,
            "on_emerge_package" : self.emerge_package,
            "on_adv_emerge_package" : self.adv_emerge_package,
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
            "on_verbose_activate" : self.verbose_set,
            "on_search_descriptions1_activate" : self.search_set,
            "on_downgrade_activate" : self.upgradeonly_set,
            "on_open_log" : self.open_log,
            "on_run_custom" : self.custom_run,
            "on_main_window_size_request" : self.size_update
            }
        self.wtree.signal_autoconnect(callbacks)
        # aliases for convenience
        self.notebook = self.wtree.get_widget("notebook")
        self.changelog = self.wtree.get_widget("changelog").get_buffer()
        self.installed_files = self.wtree.get_widget(
            "installed_files").get_buffer()
        # set unfinished items to not be sensitive
        self.wtree.get_widget("contents2").set_sensitive(gtk.FALSE)
        # self.wtree.get_widget("btn_help").set_sensitive(gtk.FALSE)
        # setup the category view
        self.category_view = CategoryView()
        self.category_view.register_callback(self.category_changed)
        self.wtree.get_widget(
            "category_scrolled_window").add(self.category_view)
        # setup the package treeview
        self.package_view = PackageView()
        self.package_view.register_callbacks(self.package_changed, None, self.pkg_path_callback)
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
        # how should we setup our saved menus?
        if self.prefs.emerge.pretend:
            self.wtree.get_widget("pretend1").set_active(gtk.TRUE)
        if self.prefs.emerge.fetch:
            self.wtree.get_widget("fetch").set_active(gtk.TRUE)
        if self.prefs.emerge.verbose:
            self.wtree.get_widget("verbose4").set_active(gtk.TRUE)
        if self.prefs.main.search_desc:
            self.wtree.get_widget("search_descriptions1").set_active(gtk.TRUE)
        # restore last window width/height
        self.wtree.get_widget("main_window").resize(self.prefs.main.width,
                                                    self.prefs.main.height)
        # move horizontal and vertical panes
        #dprint("MAINWINDOW: __init__() before hpane; %d, vpane; %d" %(self.prefs.main.hpane, self.prefs.main.vpane))
        self.wtree.get_widget("hpane").set_position(self.prefs.main.hpane)
        self.wtree.get_widget("vpane").set_position(self.prefs.main.vpane)
        # initialize some variable to fix the hpane jump bug
        self.hpane_bug_count = 0
        self.hpane_bug = True
        # initialize our data
        self.init_data()
        self.current_category = None
        self.current_package_name = None
        self.current_package_path = None
        # set if we are root or not
        self.is_root = is_root()
        if self.prefs.main.show_nag_dialog:
            # let the user know if he can emerge or not
            self.check_for_root()
        # create and start our process manager
        self.process_manager = ProcessManager(environment(), self.prefs, self.config, False)
        dprint("MAIN: Showing main window")

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
        self.current_package_cursor = None
        self.current_category_cursor = None
        # descriptions loaded?
        self.desc_loaded = False
        self.search_loaded = False
        self.current_package_path = None
        # view filter setting
        self.last_view_setting = None
        # set notebook tabs to load new package info
        self.deps_filled = self.changelog_loaded = self.installed_loaded = False
        # declare the database
        self.db = None
        # load the db
        self.db_thread = portagelib.DatabaseReader()
        self.db_thread.start()
        self.reload = False
        self.db_timeout = gtk.timeout_add(100, self.update_db_read)
        # set status
        self.set_statusbar("Reading package database: %i packages read"
                           % 0)
    def reload_db(self):
        dprint("TERMINAL: reload_db() callback")
        # upgrades loaded?
        # reset so that it reloads the upgrade list
        self.upgrades_loaded = False
        # upgrade loading callback
        self.upgrades_loaded_callback = None
        self.search_loaded = False
        self.current_package_path = None
        # load the db
        self.db_thread = portagelib.DatabaseReader()
        self.db_thread.start()
        self.reload = True
        self.db_timeout = gtk.timeout_add(100, self.update_db_read)
        # set status
        self.set_statusbar("Reading package database: %i packages read"
                           % 0)

    def pkg_path_callback(self, path):
        """callback function to save the path to the package that
        matched the name passed to the populate() in PackageView"""
        self.current_package_path = path
        return

    def check_for_root(self):
        """figure out if the user can emerge or not..."""
        if not self.is_root:
            self.no_root_dialog = SingleButtonDialog("You are not root!",
                            self.wtree.get_widget("main_window"),
                            "You will not be able to emerge, unmerge,"
                            " upgrade or sync!",
                            self.remove_nag_dialog,
                            "_Ok")

    def remove_nag_dialog(self, widget, response):
        """ Remove the nag dialog and set it to not display next time """
        self.no_root_dialog.destroy()
        self.prefs.main.show_nag_dialog = False

    def set_statusbar(self, string):
        """Update the statusbar without having to use push and pop."""
        statusbar = self.wtree.get_widget("statusbar1")
        statusbar.pop(0)
        statusbar.push(0, string)

    def update_db_read(self):
        """Update the statusbar according to the number of packages read."""
        count = 0
        if not self.db_thread.done:
            self.set_statusbar("Reading package database: %i packages read"
                               % self.db_thread.count)
            count = self.db_thread.count
        elif self.db_thread.error:
            # todo: display error dialog instead
            self.db_thread.join()
            self.set_statusbar(self.db_thread.error.decode('ascii', 'replace'))
            return gtk.FALSE  # disconnect from timeout
        else:
            dprint("MAINWINDOW: db_thread is done...")
            dprint("MAINWINDOW: db_thread.join...")
            self.db_thread.join()
            dprint("MAINWINDOW: db_thread.join is done...")
            self.db = self.db_thread.get_db()
            self.set_statusbar("Populating tree ...")
            self.update_statusbar(self.SHOW_ALL)
            dprint("MAINWINDOW: setting menubar,toolbar,etc to sensitive...")
            self.wtree.get_widget("menubar").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("toolbar").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("view_filter").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("search_entry").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("btn_search").set_sensitive(gtk.TRUE)
            # make sure we search again if we reloaded!
            view_filter = self.wtree.get_widget("view_filter")
            if view_filter.get_history() == self.SHOW_SEARCH:
                #dprint("MAINWINDOW: update_db_read()... Search view")
                # update the views by calling view_filter_changed
                self.view_filter_changed(view_filter)
                if self.reload:
                    # reset _last_selected so it thinks this package is new again
                    self.package_view._last_selected = None
                    if self.current_package_cursor[0]: # should fix a type error in set_cursor; from pycrash report
                        # re-select the package
                        self.package_view.set_cursor(self.current_package_cursor[0],
                                                     self.current_package_cursor[1])
            elif self.reload and (view_filter.get_history() == self.SHOW_ALL or \
                                  view_filter.get_history() == self.SHOW_INSTALLED) and \
                                  self.current_category_cursor != None:
                #dprint("MAINWINDOW: update_db_read()... self.reload=True ALL or INSTALLED view")
                # reset _last_selected so it thinks this category is new again
                self.category_view._last_selected = None
                dprint("MAINWINDOW: re-select the category")
                # re-select the category
                self.category_view.set_cursor(self.current_category_cursor[0],
                                              self.current_category_cursor[1])
                dprint("MAINWINDOW: reset _last_selected so it thinks this package is new again")
                # reset _last_selected so it thinks this package is new again
                self.package_view._last_selected = None
                dprint("MAINWINDOW: re-select the package")
                # re-select the package
                if self.current_package_path <> None:
                    self.package_view.set_cursor(self.current_package_path,
                                                 self.current_package_cursor[1])
            else:
                #dprint("MAINWINDOW: update_db_read()... must be an upgradeable view")
                self.package_view.clear()
                self.set_package_actions_sensitive(False, None)
                #self.category_view.populate(self.db.categories.keys(), self.current_category)
                # update the views by calling view_filter_changed
                self.view_filter_changed(view_filter)
            dprint("MAINWINDOW: Made it thru a reload, returning...")
            self.reload = False
            return gtk.FALSE  # disconnect from timeout
        dprint("MAINWINDOW: returning from update_db_read() count=%d" %count)
        return gtk.TRUE

    def setup_command(self, package_name, command):
        """Setup the command to run or not"""
        if self.is_root or (self.prefs.emerge.pretend and
                            command[:11] != "emerge sync"):
            if self.prefs.emerge.pretend:
                callback = lambda: None  # a function that does nothing
            elif package_name == "Sync":
                callback = self.init_data
            else:
                callback = self.reload_db
            #ProcessWindow(command, env, self.prefs, callback)
            self.process_manager.add_process(package_name, command, callback)
        else:
            dprint("MAIN: Sorry, you aren't root! -> " + command)
            self.sorry_dialog = SingleButtonDialog("You are not root!",
                    self.wtree.get_widget("main_window"),
                    "Please run Porthole as root to emerge packages!",
                    None, "_Ok")
            return 0
        return 1
    
    def pretend_set(self, widget):
        """Set whether or not we are going to use the --pretend flag"""
        self.prefs.emerge.pretend = widget.get_active()

    def fetch_set(self, widget):
        """Set whether or not we are going to use the --fetchonly flag"""
        self.prefs.emerge.fetch = widget.get_active()

    def verbose_set(self, widget):
        """Set whether or not we are going to use the --verbose flag"""
        self.prefs.emerge.verbose = widget.get_active()

    def upgradeonly_set(self, widget):
        """Set whether or not we are going to use the --upgradeonly flag"""
        self.prefs.emerge.upgradeonly = (not widget.get_active())

    def search_set(self, widget):
        """Set whether or not to search descriptions"""
        self.prefs.main.search_desc = widget.get_active()

    def emerge_package(self, widget):
        """Emerge the currently selected package."""
        package = get_treeview_selection(self.package_view, 2)
        self.setup_command(package.get_name(), "emerge" +
            self.prefs.emerge.get_string() + package.full_name)

    def adv_emerge_package(self, widget):
        """Advanced emerge of the currently selected package."""
        package = get_treeview_selection(self.package_view, 2)
        # Activate the advanced emerge dialog window
        dialog = AdvancedEmergeDialog(self.prefs, package, self.setup_command)

    def unmerge_package(self, widget):
        """Unmerge the currently selected package."""
        package = get_treeview_selection(self.package_view, 2)
        self.setup_command(package.get_name(), "emerge unmerge" +
                self.prefs.emerge.get_string() + package.full_name)

    def sync_tree(self, widget):
        """Sync the portage tree and reload it when done."""
        sync = "emerge sync"
        if self.prefs.emerge.verbose:
            sync += " --verbose"
        if self.prefs.emerge.nospinner:
            sync += " --nospinner "
        self.setup_command("Emerge Sync", sync)

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
            dprint("MAIN: Updating packages...")
            for package in packages_list.split():
                if not self.setup_command(package.split('/')[1], "emerge -u" +
                            self.prefs.emerge.get_string() + package):
                    return
        else:
            dprint("MAIN: Upgrades not loaded; upgrade world?")
            self.upgrades_loaded_dialog = YesNoDialog("Upgrade requested",
                    self.wtree.get_widget("main_window"),
                    "Do you want to upgrade all packages in your world file?",
                     self.upgrades_loaded_dialog_response)

    def upgrades_loaded_dialog_response(self, widget, response):
        """ Get and parse user's response """
        if response == 0: # Yes was selected; upgrade all
            self.load_upgrades_list()
            self.upgrades_loaded_callback = self.upgrade_packages
        else:
            # load the upgrades view to select which packages
            self.wtree.get_widget("view_filter").set_history(3)
        # get rid of the dialog
        self.upgrades_loaded_dialog.destroy()

    def load_descriptions_list(self):
        """ Load a list of all descriptions for searching """
        self.desc_dialog = SingleButtonDialog("Please Wait!",
                self.wtree.get_widget("main_window"),
                "Loading package descriptions...",
                self.desc_dialog_response, "_Cancel", True)
        self.desc_thread = DescriptionReader(self.db.list)
        self.desc_thread.start()
        gtk.timeout_add(100, self.desc_thread_update)

    def desc_dialog_response(self, widget, response):
        """ Get response from description loading dialog """
        self.desc_thread.please_die()
        self.desc_thread.join()
        self.desc_dialog.destroy()

    def desc_thread_update(self):
        """ Update status of description loading process """
        if self.desc_thread.done:
            # grab the db
            self.desc_db = self.desc_thread.descriptions
            if not self.desc_thread.cancelled:
                self.desc_loaded = True
                # search with descriptions
                self.package_search(None)
			# kill off the thread
            self.desc_thread.join()
            self.desc_dialog.destroy()
            return gtk.FALSE
        else:
            # print self.desc_thread.count
            if self.db:
                fraction = self.desc_thread.count / float(len(self.db.list))
                self.desc_dialog.progbar.set_text(str(int(fraction * 100)) + "%")
                self.desc_dialog.progbar.set_fraction(fraction)
        return gtk.TRUE

    def package_search(self, widget):
        """Search package db with a string and display results."""
        self.clear_notebook()
        if not self.desc_loaded and self.prefs.main.search_desc:
            self.load_descriptions_list()
            return
        tmp_search_term = self.wtree.get_widget("search_entry").get_text()
        #dprint(tmp_search_term)
        if tmp_search_term:
            search_term = ''
            Plus_exeption_count = 0
            for char in tmp_search_term:
                #dprint(char)
                if char in EXCEPTION_LIST:# =="+":
                    dprint("MAINWINDOW: package_search()  '%s' exception found" %char)
                    char = "\\" + char
                search_term += char 
            dprint("MAINWINDOW: package_search() ===> escaped search_term = :%s" %search_term)
            search_results = self.package_view.search_model
            search_results.clear()
            re_object = re.compile(search_term, re.I)
            count = 0
            # no need to sort self.db.list; it is already sorted
            for name, data in self.db.list:
                searchstrings = [name]
                if self.prefs.main.search_desc:
                    desc = self.desc_db[name]
                    searchstrings.append(desc)
                if True in map(lambda s: bool(re_object.search(s)),
                               searchstrings):
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
        dialog = AboutDialog(self.prefs)

    def category_changed(self, category):
        """Catch when the user changes categories."""
        # log the new category for reloads
        self.current_category = category
        self.current_category_cursor = self.category_view.get_cursor()
        if not self.reload:
            self.current_package_cursor = None
        #dprint("Category cursor = ")
        #dprint(self.current_category_cursor)
        mode = self.wtree.get_widget("view_filter").get_history()
        if not category:
            packages = None
        elif mode == self.SHOW_ALL:
            packages = self.db.categories[category]
        elif mode == self.SHOW_INSTALLED:
            packages = self.db.installed[category]
        else:
            raise Exception("The programmer is stupid.");
        self.package_view.populate(packages, self.current_package_name)
        #self.package_view.populate(packages)
        self.clear_notebook()

    def package_changed(self, package):
        """Catch when the user changes packages."""
        #dprint("MAINWINDOW: package_changed()")
        # log the new package for db reloads
        self.current_package_name = package.get_name()
        self.current_package_cursor = self.package_view.get_cursor()
        self.current_package_path = self.current_package_cursor[0]
        #dprint("Package name= %s, cursor = " %str(self.current_package_name))
        #dprint(self.current_package_cursor)
        # the notebook must be sensitive before anything is displayed
        # in the tabs, especially the deps_view
        self.set_package_actions_sensitive(gtk.TRUE, package)
        self.summary.update_package_info(package)
        # if the user is looking at the deps we need to update them
        cur_page = self.notebook.get_current_page()
        # reset notebook tabs to reload new package info
        self.deps_filled = self.changelog_loaded = self.installed_loaded = False
        if cur_page == 1:
            self.deps_view.fill_depends_tree(self.deps_view, package)
            self.deps_filled = True
        elif cur_page == 2:
            self.load_changelog(package)
            self.changelog_loaded = True
        elif cur_page == 3:
            self.load_installed_files(package)
            self.installed_loaded = True

    def notebook_changed(self, widget, pointer, index):
        """Catch when the user changes the notebook"""
        package = get_treeview_selection(self.package_view, 2)
        if index == 1:
            if not self.deps_filled:
                # fill the deps view!
                self.deps_view.fill_depends_tree(self.deps_view, package)
                self.deps_filled = True
        elif index == 2:
            if not self.changelog_loaded:
                # fill in the change log
                self.load_changelog(package)
                self.changelog_loaded = True
        elif index == 3:
            if not self.installed_loaded:
                # load list of installed files
                self.load_installed_files(package)
                self.installed_loaded = True

    def load_changelog(self, package):
        """ Load and display the changelog for a package """
        if package:
            try:
                f = open(portagelib.portdir + '/' + package.full_name
                        + "/ChangeLog")
                data = f.read(); f.close()
                if data:
                    self.changelog.set_text(str(data).encode("utf8",'replace'))
                else:
                    self.changelog.set_text("Change log is Empty")
            except:
                dprint("MAIN: Error opening changelog for " + package.full_name)
                self.changelog.set_text("No Change Log Available")
        else:
            dprint("MAIN: No package sent to load_changelog!")
            self.changelog.set_text("No Change Log Available")

    def load_installed_files(self, package):
        """Obtain and display list of installed files for a package,
        if installed."""
        if package:
            installed = package.get_installed()
            is_installed = installed and gtk.TRUE or gtk.FALSE
            self.wtree.get_widget(
                "installed_files_scrolled_window").set_sensitive(is_installed)
            if is_installed:
                installed.sort()
                installed_files = portagelib.get_installed_files(installed[-1])
                self.installed_files.set_text(
                    str(len(installed_files)) + " installed files:\n\n"
                    + "\n".join(installed_files))
            else:
                self.installed_files.set_text("Not installed")
        else:
            dprint("MAIN: No package sent to load_installed_files!")
            self.installed_files.set_text("No data currently available.\n\
                                           The package may not be installed")

    SHOW_ALL = 0
    SHOW_INSTALLED = 1
    SHOW_SEARCH = 2
    SHOW_UPGRADE = 3
    def view_filter_changed(self, widget):
        """Update the treeviews for the selected filter"""
        dprint("MAINWINDOW: view_filter_changed()")
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
        elif index == self.SHOW_SEARCH:
            if not self.search_loaded:
                self.set_package_actions_sensitive(False, None)
                self.category_view.populate(self.db.categories.keys())
                self.package_view.size = 0
                self.package_search(None)
                self.search_loaded = True
            cat_scroll.hide();
            dprint("MAIN: Showing search results")
            self.package_view.set_view(self.package_view.SEARCH_RESULTS)
        elif index == self.SHOW_UPGRADE:
            if not self.upgrades_loaded:
                self.load_upgrades_list()
            else:
                # already loaded, just show them!
                cat_scroll.hide();
                self.package_view.set_view(self.package_view.UPGRADABLE)
                self.summary.update_package_info(None)
        # clear the notebook tabs
        self.clear_notebook()
        if self.last_view_setting != index:
            dprint("MAINWINDOW: view_filter_changed(); last_view_setting changed")
            self.last_view_setting = index
            self.current_category = None
            self.current_package_cursor = None
            

    def load_upgrades_list(self):
        # upgrades are not loaded, create dialog and load them
        self.wait_dialog = SingleButtonDialog("Please Wait!",
                self.wtree.get_widget("main_window"),
                "Loading upgradable packages list...",
                self.wait_dialog_response, "_Cancel", True)
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
        else: 
            try:
                fraction = self.ut.count / float(self.db.installed_count)
                self.wait_dialog.progbar.set_text(str(int(fraction * 100)) + "%")
                self.wait_dialog.progbar.set_fraction(fraction)
            except:
                pass
        return gtk.TRUE

    def update_statusbar(self, mode):
        """Update the statusbar for the selected filter"""
        text = "(undefined) Statusbar not yet available for this view"
        if mode == self.SHOW_ALL:
            if not self.db:
                dprint("MAINWINDOW: attempt to update status bar with no db assigned")
            else:
                text = "%d packages in %d categories" % (len(self.db.list),
                                                         len(self.db.categories))
        elif mode == self.SHOW_INSTALLED:
            if not self.db:
                dprint("MAINWINDOW: attempt to update status bar with no db assigned")
            else:
                text = "%d packages in %d categories" % (self.db.installed_count,
                                                         len(self.db.installed))
        elif mode == self.SHOW_SEARCH:
            text = "%d matches found" % self.package_view.search_model.size
        self.set_statusbar(text)

    def set_package_actions_sensitive(self, enabled, package = None):
        """Sets package action buttons/menu items to sensitive or not"""
        #dprint("MAINWINDOW: set_package_actions_sensitive(%d)" %enabled)
        self.wtree.get_widget("emerge_package1").set_sensitive(enabled)
        self.wtree.get_widget("adv_emerge_package1").set_sensitive(enabled)
        self.wtree.get_widget("unmerge_package1").set_sensitive(enabled)
        self.wtree.get_widget("btn_emerge").set_sensitive(enabled)
        self.wtree.get_widget("btn_adv_emerge").set_sensitive(enabled)
        if not enabled or enabled and package.is_installed:
            #dprint("MAINWINDOW: set_package_actions_sensitive() setting unmerge to %d" %enabled)
            self.wtree.get_widget("btn_unmerge").set_sensitive(enabled)
            self.wtree.get_widget("unmerge_package1").set_sensitive(enabled)
        else:
            #dprint("MAINWINDOW: set_package_actions_sensitive() setting unmerge to %d" %(not enabled))
            self.wtree.get_widget("btn_unmerge").set_sensitive(not enabled)
            
            self.wtree.get_widget("unmerge_package1").set_sensitive(not enabled)
        self.notebook.set_sensitive(enabled)

    def size_update(self, widget, gbox):
        """ Store the window and pane positions """
        # bugfix for hpane jump bug
        if self.hpane_bug:
            if self.hpane_bug_count == 2: # this is when the bug caused the jump
                dprint("MAIN: hpane bugfix activated")
                # reset it back to where it should be
                self.wtree.get_widget("hpane").set_position(self.prefs.main.hpane)
                self.hpane_bug = False
            else:
                self.hpane_bug_count += 1
        pos = widget.get_size()
        self.prefs.main.width = pos[0]
        self.prefs.main.height = pos[1]
        self.prefs.main.hpane = self.wtree.get_widget("hpane").get_position()
        self.prefs.main.vpane = self.wtree.get_widget("vpane").get_position()
        #dprint("MAINWINDOW: size_update() hpane; %d, vpane; %d" \
        #       %(self.prefs.main.hpane, self.prefs.main.vpane))

    def clear_notebook(self):
        """ Clear all notebook tabs & disble them """
        #dprint("MAINWINDOW: clear_notebook()")
        self.summary.update_package_info(None)
        self.set_package_actions_sensitive(gtk.FALSE)
        self.deps_view.clear()
        self.changelog.set_text('')
        self.installed_files.set_text('')

    def open_log(self, widget):
        """ Open a log of a previous emerge in a new terminal window """
        newterm = ProcessManager(environment(), self.prefs, self.config, True)
        newterm.do_open(widget)

    def custom_run(self, widget):
        """ Run a custom command in the terminal window """
        #dprint("MAINWINDOW: entering custom_run")
        #dprint(self.prefs.run_dialog.history)
        get_command = RunDialog(self.prefs, self.setup_command)


class CommonReader(threading.Thread):
    """ Common data reading class that works in a seperate thread """
    def __init__(self):
        """ Initialize """
        threading.Thread.__init__(self)
        # for keeping status
        self.count = 0
        # we aren't done yet
        self.done = False
        # cancelled will be set when the thread should stop
        self.cancelled = False
        # quit even if thread is still running
        self.setDaemon(1)

    def please_die(self):
        """ Tell the thread to die """
        self.cancelled = True

class UpgradableReader(CommonReader):
    """ Read available upgrades and store them in a treemodel """
    def __init__(self, upgrade_model, installed):
        """ Initialize """
        CommonReader.__init__(self)
        self.upgrade_results = upgrade_model
        self.installed_items = installed
    
    def run(self):
        """fill upgrade tree"""
        self.upgrade_results.clear()    # clear the treemodel
        installed = []
        # find upgradable packages
        for cat, packages in self.installed_items:
            for name, package in packages.items():
                self.count += 1
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

class DescriptionReader(CommonReader):
    """ Read and store package descriptions for searching """
    def __init__(self, packages):
        """ Initialize """
        CommonReader.__init__(self)
        self.packages = packages

    def run(self):
        """ Load all descriptions """
        self.descriptions = {}
        for name, package in self.packages:
            if self.cancelled: self.done = True; return
            self.descriptions[name] = package.get_properties().description
            if not self.descriptions[name]:
                dprint("MAIN: No description for " + name)
            self.count += 1
        self.done = True
