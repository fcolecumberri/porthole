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
from portagelib import World

from gettext import gettext as _
from about import AboutDialog
from utils import get_icon_for_package, get_icon_for_upgrade_package, is_root, dprint, \
     get_treeview_selection, YesNoDialog, SingleButtonDialog, environment, \
     pretend_check, help_check #,  get_world
#from process import ProcessWindow  # no longer used in favour of terminal and would need updating to be used
from summary import Summary
from terminal import ProcessManager
from views import CategoryView, PackageView, DependsView, CommonTreeView
from depends import DependsTree
from command import RunDialog
from advemerge import AdvancedEmergeDialog
from plugin import PluginGUI, PluginManager
from readers import UpgradableReader, DescriptionReader
from loaders import *


EXCEPTION_LIST = ['.','^','$','*','+','?','(',')','\\','[',']','|','{','}']
SHOW_ALL = 0
SHOW_INSTALLED = 1
SHOW_SEARCH = 2
SHOW_UPGRADE = 3
ON = True
OFF = False

class MainWindow:
    """Main Window class to setup and manage main window interface."""
    def __init__(self, preferences = None, config = None):
        # setup prefs
        self.prefs = preferences
        self.config = config
        # setup glade
        self.gladefile = self.prefs.DATA_PATH + "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "main_window", self.prefs.APP)
        # register callbacks  note: gtk.mainquit deprecated
        callbacks = {
            "on_main_window_destroy" : self.goodbye,
            "on_quit1_activate" : self.quit,
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
            "on_upgradeonly_activate" : self.upgradeonly_set,
            "on_open_log" : self.open_log,
            "on_run_custom" : self.custom_run,
            "on_reload_db" : self.reload_db,
            "on_re_init_portage" : self.re_init_portage,
            "on_cancel_btn" : self.on_cancel_btn,
            "on_main_window_size_request" : self.size_update,
            "on_plugin_settings_activate" : self.plugin_settings_activate
        }
        self.wtree.signal_autoconnect(callbacks)
        self.set_statusbar2("Starting")
        # aliases for convenience
        self.mainwindow = self.wtree.get_widget("main_window")
        self.notebook = self.wtree.get_widget("notebook")
        self.installed_window = self.wtree.get_widget("installed_files_scrolled_window")
        self.changelog = self.wtree.get_widget("changelog").get_buffer()
        self.installed_files = self.wtree.get_widget("installed_files").get_buffer()
        self.ebuild = self.wtree.get_widget("ebuild").get_buffer()
        # set unfinished items to not be sensitive
        #self.wtree.get_widget("contents2").set_sensitive(gtk.FALSE)
        # self.wtree.get_widget("btn_help").set_sensitive(gtk.FALSE)
        # setup the category view
        self.category_view = CategoryView()
        self.category_view.register_callback(self.category_changed)
        result = self.wtree.get_widget("category_scrolled_window").add(self.category_view)
        # setup the package treeview
        self.package_view = PackageView()
        self.package_view.register_callbacks(self.package_changed, None, self.pkg_path_callback)
        result = self.wtree.get_widget("package_scrolled_window").add(self.package_view)
        # setup the dependency treeview
        self.deps_view = DependsView()
        result = self.wtree.get_widget("dependencies_scrolled_window").add(self.deps_view)
        # summary view
        scroller = self.wtree.get_widget("summary_text_scrolled_window");
        self.summary = Summary()
        result = scroller.add(self.summary)
        self.summary.show()
        # how should we setup our saved menus?
        if self.prefs.emerge.pretend:
            self.wtree.get_widget("pretend1").set_active(gtk.TRUE)
        if self.prefs.emerge.fetch:
            self.wtree.get_widget("fetch").set_active(gtk.TRUE)
        if self.prefs.emerge.upgradeonly :
            self.wtree.get_widget("upgradeonly").set_active(gtk.TRUE)
        if self.prefs.emerge.verbose:
            self.wtree.get_widget("verbose4").set_active(gtk.TRUE)
        if self.prefs.main.search_desc:
            self.wtree.get_widget("search_descriptions1").set_active(gtk.TRUE)
        # setup a convienience tuple
        self.tool_widgets = ["emerge_package1","adv_emerge_package1","unmerge_package1","btn_emerge",
                     "btn_adv_emerge","btn_unmerge", "btn_sync"]
        self.widget = {}
        for x in self.tool_widgets:
            self.widget[x] = self.wtree.get_widget(x)
            if not self.widget[x]:
                dprint("MAINWINDOW: __init__(); Failure to obtain widget '%s'" %x)
        # get an empty tooltip
        self.synctooltip = gtk.Tooltips()
        self.sync_tip = _(" Syncronise Package Database \n The last sync was done:\n")
        # restore last window width/height
        self.mainwindow.resize(self.prefs.main.width, self.prefs.main.height)
        # move horizontal and vertical panes
        dprint("MAINWINDOW: __init__() before hpane; %d, vpane; %d" %(self.prefs.main.hpane, self.prefs.main.vpane))
        self.wtree.get_widget("hpane").set_position(self.prefs.main.hpane)
        self.wtree.get_widget("vpane").set_position(self.prefs.main.vpane)
        # Intercept the window delete event signal
        self.mainwindow.connect('delete-event', self.confirm_delete)
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
        #Plugin-related statements
        self.needs_plugin_menu = False
        dprint( "MAIN: Path List for plugins:" ) 
        dprint( self.prefs.plugins.path_list )
        self.plugin_root_menu = gtk.MenuItem("Active Plugins")
        self.plugin_menu = gtk.Menu()
        self.plugin_root_menu.set_submenu(self.plugin_menu)
        self.wtree.get_widget("menubar").append(self.plugin_root_menu)
        self.plugin_manager = PluginManager( self.prefs.plugins.path_list, self )
        dprint("MAIN: Showing main window")


    def init_data(self):
        # set things we can't do unless a package is selected to not sensitive
        self.set_package_actions_sensitive(gtk.FALSE)
        dprint("MAINWINDOW: init_data(); Initializing data")
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
        self.deps_filled = self.changelog_loaded = self.installed_loaded = self.ebuild_loaded = False
        # declare the database
        self.db = None
        self.ut_running = False
        self.ut = None
        # load the db
        self.dbtime = 0
        self.db_thread = portagelib.DatabaseReader()
        self.db_thread.start()
        self.db_thread_running = True
        self.reload = False
        self.db_timeout = gtk.timeout_add(100, self.update_db_read)
        self.get_sync_time()
        self.synctooltip.set_tip(self.widget["btn_sync"], self.sync_tip + self.last_sync)
        # set status
        #self.set_statusbar(_("Obtaining package list "))
        self.status_root = _("Loading database")
        self.set_statusbar2(self.status_root)
        self.progressbar = self.wtree.get_widget("progressbar1")
        self.set_cancel_btn(OFF)

    def reload_db(self, *widget):
        dprint("TERMINAL: reload_db() callback")
        if self.db_thread_running or self.ut_running:
            if self.db_thread_running:
                dprint("MAINWINDOW: reload_db(); killing db thread")
                self.db_thread.please_die()
                self.db_thread_running = False
            else: # self.ut_running
                dprint("MAINWINDOW: reload_db(); killing upgrades thread")
                self.ut.please_die()
                self.ut_running = False
            self.progress_done(True)
            # set this function to re-run after some time for the thread to stop
            self.reload_db_timeout = gtk.timeout_add(50, self.reload_db)
            return gtk.TRUE
        # upgrades loaded?
        # reset so that it reloads the upgrade list
        self.upgrades_loaded = False
        self.ut_cancelled = False
        # upgrade loading callback
        self.upgrades_loaded_callback = None
        self.search_loaded = False
        self.current_package_path = None
        # test to reset portage
        #portagelib.reload_portage()
        # load the db
        self.dbtime = 0
        self.db_thread = portagelib.DatabaseReader()
        self.db_thread.start()
        self.db_thread_running = True
        #test = 87/0  # used to test pycrash is functioning
        self.reload = True
        self.db_timeout = gtk.timeout_add(100, self.update_db_read)
        portagelib.reload_world()
        self.get_sync_time()
        self.synctooltip.set_tip(self.widget["btn_sync"], self.sync_tip + self.last_sync)
        # set status
        #self.set_statusbar(_("Obtaining package list "))
        self.status_root = _("Reloading database")
        self.set_statusbar2(self.status_root)
        return gtk.FALSE

    def get_sync_time(self):
        """gets and returns the timestamp info saved during
           the last portage tree sync"""
        self.last_sync = _("Unknown")
        try:
            f = open(portagelib.portdir + "/metadata/timestamp")
            data = f.read(); f.close()
            if data:
                try:
                    dprint("MAINWINDOW: get_sync_time(); trying utf_8 encoding")
                    self.last_sync = (str(data).decode('utf_8').encode("utf_8",'replace'))
                except:
                    try:
                        dprint("MAINWINDOW: get_sync_time(); trying iso-8859-1 encoding")
                        self.last_sync = (str(data).decode('iso-8859-1').encode('utf_8', 'replace'))
                    except:
                        dprint("MAINWINDOW: get_sync_time(); Failure = unknown encoding")
            else:
                dprint("MAINWINDOW: get_sync_time(); No data read")
        except:
            dprint("MAINWINDOW: get_sync_time(); file open or read error")

    def pkg_path_callback(self, path):
        """callback function to save the path to the package that
        matched the name passed to the populate() in PackageView"""
        self.current_package_path = path
        return

    def check_for_root(self):
        """figure out if the user can emerge or not..."""
        if not self.is_root:
            self.no_root_dialog = SingleButtonDialog(_("You are not root!"),
                            self.mainwindow,
                            _("You will not be able to emerge, unmerge,"
                            " upgrade or sync!"),
                            self.remove_nag_dialog,
                            "_Ok")

    def remove_nag_dialog(self, widget, response):
        """ Remove the nag dialog and set it to not display next time """
        self.no_root_dialog.destroy()
        self.prefs.main.show_nag_dialog = False

    def set_statusbar2(self, string):
        """Update the statusbar without having to use push and pop."""
        #dprint("MAINWINDOW: set_statusbar2(); " + string)
        statusbar2 = self.wtree.get_widget("statusbar2")
        statusbar2.pop(0)
        statusbar2.push(0, string)

    def update_db_read(self):
        """Update the statusbar according to the number of packages read."""
        #count = 0
        if not self.db_thread.done:
            self.dbtime += 1
            if self.db_thread.count > 0:
                self.set_statusbar2(self.status_root + _(": %i packages read"
                                     % self.db_thread.count))
            #count = self.db_thread.count
            #dprint("self.prefs.dbtime = ")
            #dprint(self.prefs.dbtime)
            try:
                fraction = min(1.0, max(0,(self.dbtime / float(self.prefs.dbtime))))
                self.progressbar.set_text(str(int(fraction * 100)) + "%")
                self.progressbar.set_fraction(fraction)
            except:
                pass

        elif self.db_thread.error:
            # todo: display error dialog instead
            self.db_thread.join()
            self.set_statusbar2(self.db_thread.error.decode('ascii', 'replace'))
            return gtk.FALSE  # disconnect from timeout
        else: # db_thread is done
            self.db_thread_running = False
            self.db_save_variables()
            self.progressbar.set_text("100%")
            self.progressbar.set_fraction(1.0)
            dprint("MAINWINDOW: db_thread is done...")
            dprint("MAINWINDOW: db_thread.join...")
            self.db_thread.join()
            self.db_thread_running = False
            dprint("MAINWINDOW: db_thread.join is done...")
            self.db = self.db_thread.get_db()
            self.set_statusbar2(self.status_root + _(": Populating tree"))
            self.update_statusbar(SHOW_ALL)
            #~dprint("MAINWINDOW: setting menubar,toolbar,etc to sensitive...")
            self.wtree.get_widget("menubar").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("toolbar").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("view_filter").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("search_entry").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("btn_search").set_sensitive(gtk.TRUE)
            # make sure we search again if we reloaded!
            view_filter = self.wtree.get_widget("view_filter")
            if view_filter.get_history() == SHOW_SEARCH:
                #dprint("MAINWINDOW: update_db_read()... Search view")
                # update the views by calling view_filter_changed
                self.view_filter_changed(view_filter)
                if self.reload:
                    # reset _last_selected so it thinks this package is new again
                    self.package_view._last_selected = None
                    if self.current_package_cursor != None and self.current_package_cursor[0]: # should fix a type error in set_cursor; from pycrash report
                        # re-select the package
                        self.package_view.set_cursor(self.current_package_cursor[0],
                                                     self.current_package_cursor[1])
            elif self.reload and (view_filter.get_history() == SHOW_ALL or \
                                  view_filter.get_history() == SHOW_INSTALLED) and \
                                  self.current_category_cursor != None:
                #dprint("MAINWINDOW: update_db_read()... self.reload=True ALL or INSTALLED view")
                # reset _last_selected so it thinks this category is new again
                self.category_view._last_selected = None
                #~dprint("MAINWINDOW: re-select the category")
                # re-select the category
                self.category_view.set_cursor(self.current_category_cursor[0],
                                              self.current_category_cursor[1])
                #~dprint("MAINWINDOW: reset _last_selected so it thinks this package is new again")
                # reset _last_selected so it thinks this package is new again
                self.package_view._last_selected = None
                #~dprint("MAINWINDOW: re-select the package")
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
            self.progress_done(False)
            self.view_filter_changed(view_filter)
            return gtk.FALSE  # disconnect from timeout
        #dprint("MAINWINDOW: returning from update_db_read() count=%d dbtime=%d"  %(count, self.dbtime))
        return gtk.TRUE

    def db_save_variables(self):
        """recalulates and stores persistent database variables into the prefernces"""
        self.prefs.database_size = self.db_thread.allnodes_length
        # store only the last 10 reload times
        if len(self.prefs.dbtotals)==10:
            self.prefs.dbtotals = self.prefs.dbtotals[1:]+[str(self.dbtime)]
        else:
            self.prefs.dbtotals += [str(self.dbtime)]
        # calculate the average time to use for the progress bar calculations
        total = 0
        count = 0
        for time in self.prefs.dbtotals:
            total += int(time)
            count += 1
        #dprint("MAINWINDOW: db_save_variables(); total = %d : count = %d" %(total,count))
        self.prefs.dbtime = int(total/count)
        dprint("MAINWINDOW: db_save_variables(); dbtime = %d" %self.dbtime)
        dprint("MAINWINDOW: db_save_variables(); new average load time = %d cycles" %self.prefs.dbtime)


    def setup_command(self, package_name, command):
        """Setup the command to run or not"""
        if self.is_root or (self.prefs.emerge.pretend and
                            command[:11] != "emerge sync"):
            if self.prefs.emerge.pretend or pretend_check(command) or help_check(command):
                callback = lambda: None  # a function that does nothing
            elif package_name == "Sync":
                callback = self.init_data
            else:
                callback = self.reload_db
            #ProcessWindow(command, env, self.prefs, callback)
            self.process_manager.add_process(package_name, command, callback)
        else:
            dprint("MAINWINDOW: Sorry, you aren't root! -> " + command)
            self.sorry_dialog = SingleButtonDialog(_("You are not root!"),
                    self.mainwindow,
                    _("Please run Porthole as root to emerge packages!"),
                    None, "_Ok")
            return False
        return True
   
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
        self.prefs.emerge.upgradeonly = widget.get_active()
        # reset the upgrades list due to the change
        self.upgrades_loaded = False
        view_filter = self.wtree.get_widget("view_filter")
        if view_filter.get_history() == SHOW_UPGRADE:
                #dprint("MAINWINDOW: upgradeonly_set()...reload upgradeable view")
                self.package_view.clear()
                self.set_package_actions_sensitive(False, None)
                # update the views by calling view_filter_changed
                self.view_filter_changed(view_filter)

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

    def plugin_settings_activate( self, widget ):
        """Shows the plugin settings window"""
        plugin_dialog = PluginGUI( self.prefs, self.plugin_manager )
 
    def new_plugin_menuitem( self, label ):
        dprint("MAINWINDOW: Adding new Menu Entry")
        if self.needs_plugin_menu == False:
            #Creates plugin Menu
            dprint("MAINWINDOW: Enabling Plugin Menu")
            self.plugin_root_menu.show()
            self.needs_plugin_menu = True
        new_item = gtk.MenuItem( label )
        new_item.show()
        self.plugin_menu.append( new_item )
        return new_item

    def del_plugin_menuitem( self, menuitem ):
        self.plugin_menu.remove( menuitem )
        if len(self.plugin_menu.get_children()) == 0:
            self.plugin_root_menu.hide()
            self.needs_plugin_menu = False
        del menuitem

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

    def on_cancel_btn(self, widget):
        """cancel button callback function"""
        dprint("MAINWINDOW: on_cancel_btn() callback")
        # terminate the thread
        self.ut.please_die()
        self.ut.join()
        self.progress_done(True)

    def upgrade_packages(self, widget):
        """Upgrade selected packages that have newer versions available."""
        if self.upgrades_loaded:
            dprint("MAINWINDOW: upgrade_packages() upgrades loaded")
            # create a list of packages to be upgraded
            self.packages_list = {}
            self.keyorder = []
            self.up_model = self.package_view.upgrade_model
            # read the upgrade tree into a list of packages to upgrade
            self.up_model.foreach(self.tree_node_to_list)
            #dprint(self.packages_list)
            #dprint(self.keyorder)
            for key in self.keyorder:
                if not self.packages_list[key]:
                        dprint("MAINWINDOW: upgrade_packages(); dependancy selected: " + key)
                        if not self.setup_command(key, "emerge -u --oneshot" +
                                self.prefs.emerge.get_string() + key.split('/')[1]):
                            return
                elif not self.setup_command(key, "emerge -u" +
                                self.prefs.emerge.get_string() + ' ' + key.split('/')[1]):
                    return
        else:
            dprint("MAIN: Upgrades not loaded; upgrade world?")
            self.upgrades_loaded_dialog = YesNoDialog(_("Upgrade requested"),
                    self.mainwindow,
                    _("Do you want to upgrade all packages in your world file?"),
                     self.upgrades_loaded_dialog_response)

    def tree_node_to_list(self, model, path, iter):
        """callback function from gtk.TreeModel.foreach(),
           used to add packages to an upgrades list"""
        if model.get_value(iter, 1):
            name = model.get_value(iter, 0)
	    dprint(name)
            if name not in self.keyorder:
                self.packages_list[name] = model.get_value(iter, 4) # model.get_value(iter, 2), name]
                self.keyorder = [name] + self.keyorder 
        return False


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
        self.desc_dialog = SingleButtonDialog(_("Please Wait!"),
                self.mainwindow,
                _("Loading package descriptions..."),
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
                    search_results.set_value(iter, 5, '')
                    #dprint(data.full_name + " %d" %(data.in_world))
                    search_results.set_value(iter, 4, data.in_world)
                    # set the icon depending on the status of the package
                    icon = get_icon_for_package(data)
                    view = self.package_view
                    search_results.set_value(
                        iter, 3,
                        view.render_icon(icon,
                                         size = gtk.ICON_SIZE_MENU,
                                         detail = None))
            search_results.size = count  # store number of matches
            self.wtree.get_widget("view_filter").set_history(SHOW_SEARCH)
            # in case the search view was already active
            self.update_statusbar(SHOW_SEARCH)
                
    def help_contents(self, widget):
        """Show the help file contents."""
        load_web_page('file://' + self.prefs.DATA_PATH + 'help/index.html')

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
        #dprint("Category cursor = " +str(self.current_category_cursor))
        #dprint(self.current_category_cursor[0][1])
        mode = self.wtree.get_widget("view_filter").get_history()
        if not category or self.current_category_cursor[0][1] == None:
            #dprint("MAINWINDOW: category_changed(); category=False or self.current_category_cursor[0][1]=None")
            packages = None
            self.current_package_name = None
            self.current_package_cursor = None
            self.current_package_path = None
            self.package_view.PACKAGES = 0
            self.package_view.set_view(self.package_view.PACKAGES)
            self.package_view.clear()
        elif mode == SHOW_ALL:
            packages = self.db.categories[category]
        elif mode == SHOW_INSTALLED:
            packages = self.db.installed[category]
        else:
            raise Exception("The programmer is stupid.");
        self.package_view.populate(packages, self.current_package_name)
        #self.package_view.populate(packages)
        self.clear_notebook()

    def package_changed(self, package):
        """Catch when the user changes packages."""
        dprint("MAINWINDOW: package_changed()")
        if not package:
            self.clear_notebook()
            self.current_package_name = ''
            self.current_package_cursor = self.package_view.get_cursor()
            self.current_package_path = self.current_package_cursor[0]
            return
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
        self.deps_filled = self.changelog_loaded = self.installed_loaded = self.ebuild_loaded = False
        if cur_page == 1:
            self.deps_view.fill_depends_tree(self.deps_view, package)
            self.deps_filled = True
        elif cur_page == 2:
            load_textfile(self.changelog, package, "changelog")
            self.changelog_loaded = True
        elif cur_page == 3:
            load_installed_files(self.installed_window, self.installed_files, package)
            self.installed_loaded = True
        elif cur_page == 4:
            load_textfile(self.ebuild, package, "best_ebuild")
            self.ebuild_loaded = True

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
                load_textfile(self.changelog, package, "changelog")
                self.changelog_loaded = True
        elif index == 3:
            if not self.installed_loaded:
                # load list of installed files
                load_installed_files(self.installed_window, self.installed_files, package)
                self.installed_loaded = True
        elif index == 4:
            if not self.ebuild_loaded:
                # load list of installed files
                load_textfile(self.ebuild, package, "best_ebuild")
                self.ebuild_loaded = True

    def view_filter_changed(self, widget):
        """Update the treeviews for the selected filter"""
        dprint("MAINWINDOW: view_filter_changed()")
        index = widget.get_history()
        self.update_statusbar(index)
        cat_scroll = self.wtree.get_widget("category_scrolled_window")
        if index in (SHOW_INSTALLED, SHOW_ALL):
            cat_scroll.show();
            self.category_view.populate(
                index == SHOW_ALL
                and self.db.categories.keys()
                or self.db.installed.keys())
            self.package_view.set_view(self.package_view.PACKAGES)
            self.package_view.clear()
        elif index == SHOW_SEARCH:
            if not self.search_loaded:
                self.set_package_actions_sensitive(False, None)
                self.category_view.populate(self.db.categories.keys())
                self.package_view.size = 0
                self.package_search(None)
                self.search_loaded = True
            cat_scroll.hide();
            dprint("MAIN: Showing search results")
            self.package_view.set_view(self.package_view.SEARCH_RESULTS)
        elif index == SHOW_UPGRADE:
            dprint("MAINWINDOW: view_filter_changed(); upgrade selected")
            cat_scroll.hide();
            self.package_view.set_view(self.package_view.UPGRADABLE)
            if not self.upgrades_loaded:
                self.load_upgrades_list()
                self.package_view.clear()
                dprint("MAINWINDOW: view_filter_changed(); back from load_upgrades_list()")
            else:
                # already loaded, just show them!
                dprint("MAINWINDOW: view_filter_changed(); showing loaded upgrades")
                #self.package_view.set_view(self.package_view.UPGRADABLE)
                self.summary.update_package_info(None)
        # clear the notebook tabs
        self.clear_notebook()
        #if self.last_view_setting != index:
        dprint("MAINWINDOW: view_filter_changed(); last_view_setting changed")
        self.last_view_setting = index
        self.current_category = None
        self.category_view.last_category = None
        self.current_package_cursor = None
            

    def load_upgrades_list(self):
        # upgrades are not loaded, create dialog and load them
        self.set_statusbar2(_("Loading upgradable list"))
        # create upgrade thread for loading the upgrades
        self.ut = UpgradableReader(self.package_view, self.db.installed.items(),
                                   self.prefs.emerge.upgradeonly, self.prefs.views )
        self.ut.start()
        self.ut_running = True
        dprint("MAINWINDOW: load_upgrades_list(); starting upgrades thread")
        self.build_deps = False
        # add a timeout to check if thread is done
        gtk.timeout_add(200, self.update_upgrade_thread)
        self.set_cancel_btn(ON)

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
            self.ut_running = False
            self.upgrades_loaded = True
            self.progress_done(True)
            view_filter = self.wtree.get_widget("view_filter")
            self.view_filter_changed(view_filter)
            if self.upgrades_loaded_callback:
                self.upgrades_loaded_callback(None)
                self.upgrades_loaded_callback = None
            else:
                if self.last_view_setting == SHOW_UPGRADE:
                    self.package_view.set_view(self.package_view.UPGRADABLE)
                    self.summary.update_package_info(None)
                    #self.wtree.get_widget("category_scrolled_window").hide()
            return gtk.FALSE
        else:
            if self.ut_running:
                try:
                    if self.build_deps:
                        fraction = (self.ut.world_count + self.ut.dep_count) / float(self.ut.upgrade_total)
                        self.progressbar.set_text(str(int(fraction * 100)) + "%")
                        self.progressbar.set_fraction(fraction)
                    else:
                        fraction = self.ut.count / float(self.db.installed_count)
                        self.progressbar.set_text(str(int(fraction * 100)) + "%")
                        self.progressbar.set_fraction(fraction)
                        if fraction == 1:
                            self.build_deps = True
                            self.set_statusbar2(_("Building Dependancy trees"))
                except:
                    pass
        return gtk.TRUE

    def progress_done(self, button_off=False):
        """clears the progress bar"""
        if button_off:
            self.set_cancel_btn(OFF)
        self.progressbar.set_text("")
        self.progressbar.set_fraction(0)
        self.status_root = _("Done: ")
        self.set_statusbar2(self.status_root)

    def set_cancel_btn(self, state):
            self.wtree.get_widget("btn_cancel").set_sensitive(state)

    def update_statusbar(self, mode):
        """Update the statusbar for the selected filter"""
        text = ""
        if mode == SHOW_ALL:
            if not self.db:
                dprint("MAINWINDOW: attempt to update status bar with no db assigned")
            else:
                text = _("%d packages in %d categories" % (len(self.db.list),
                                                         len(self.db.categories)))
        elif mode == SHOW_INSTALLED:
            if not self.db:
                dprint("MAINWINDOW: attempt to update status bar with no db assigned")
            else:
                text = _("%d packages in %d categories" % (self.db.installed_count,
                                                         len(self.db.installed)))
        elif mode == SHOW_SEARCH:
            text = _("%d matches found" % self.package_view.search_model.size)

        elif mode == SHOW_UPGRADE:
            if not self.ut:
                dprint("MAINWINDOW: attempt to update status bar with no upgrade thread assigned")
            else:
                text = _("%d world, %d dependencies" % (self.ut.world_count,
                                                         self.ut.dep_count))

        self.set_statusbar2(self.status_root + text)

    def set_package_actions_sensitive(self, enabled, package = None):
        """Sets package action buttons/menu items to sensitive or not"""
        #dprint("MAINWINDOW: set_package_actions_sensitive(%d)" %enabled)
        self.widget["emerge_package1"].set_sensitive(enabled)
        self.widget["adv_emerge_package1"].set_sensitive(enabled)
        self.widget["unmerge_package1"].set_sensitive(enabled)
        self.widget["btn_emerge"].set_sensitive(enabled)
        self.widget["btn_adv_emerge"].set_sensitive(enabled)
        if not enabled or enabled and package.is_installed:
            #dprint("MAINWINDOW: set_package_actions_sensitive() setting unmerge to %d" %enabled)
            self.widget["btn_unmerge"].set_sensitive(enabled)
            self.widget["unmerge_package1"].set_sensitive(enabled)
        else:
            #dprint("MAINWINDOW: set_package_actions_sensitive() setting unmerge to %d" %(not enabled))
            self.widget["btn_unmerge"].set_sensitive(not enabled)
            
            self.widget["unmerge_package1"].set_sensitive(not enabled)
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
                del self.hpane_bug_count
            else:
                self.hpane_bug_count += 1
        pos = widget.get_size()
        self.prefs.main.width = pos[0]
        self.prefs.main.height = pos[1]
        self.prefs.main.hpane = self.wtree.get_widget("hpane").get_position()
        self.prefs.main.vpane = self.wtree.get_widget("vpane").get_position()
        #~ dprint("MAINWINDOW: size_update() hpane; %d, vpane; %d" \
               #~ %(self.prefs.main.hpane, self.prefs.main.vpane))

    def clear_notebook(self):
        """ Clear all notebook tabs & disable them """
        #dprint("MAINWINDOW: clear_notebook()")
        self.summary.update_package_info(None)
        self.set_package_actions_sensitive(gtk.FALSE)
        self.deps_view.clear()
        self.changelog.set_text('')
        self.installed_files.set_text('')
        self.ebuild.set_text('')

    def open_log(self, widget):
        """ Open a log of a previous emerge in a new terminal window """
        newterm = ProcessManager(environment(), self.prefs, self.config, True)
        newterm.do_open(widget)

    def custom_run(self, widget):
        """ Run a custom command in the terminal window """
        #dprint("MAINWINDOW: entering custom_run")
        #dprint(self.prefs.run_dialog.history)
        get_command = RunDialog(self.prefs, self.setup_command)

    def re_init_portage(self, *widget):
        """re-initializes the imported portage modules in order to see changines in any config files
        e.g. /etc/make.conf USE flags changed"""
        portagelib.reload_portage()
        portagelib.reset_use_flags()
        if  self.current_package_cursor != None and self.current_package_cursor[0]: # should fix a type error in set_cursor; from pycrash report
            # reset _last_selected so it thinks this package is new again
            self.package_view._last_selected = None
            # re-select the package
            self.package_view.set_cursor(self.current_package_cursor[0],
            self.current_package_cursor[1])

    def quit(self, widget):
        if not self.confirm_delete():
            self.goodbye(None)
        return

    def goodbye(self, widget):
        """Main window quit function"""
        dprint("MAINWINDOW: goodbye(); quiting now")
        try: # for >=pygtk-2.3.94
            dprint("MAINWINDOW: gtk.main_quit()")
            gtk.main_quit()
        except: # use the depricated function
            dprint("MAINWINDOW: gtk.mainquit()")
            gtk.mainquit

    def confirm_delete(self, widget = None, *event):
        """Check that there are no running processes & confirm the kill before doing it"""
        if self.process_manager.task_completed:
            return False
        err = _("Confirm: Kill the Running Process in the Terminal")
        dialog = gtk.MessageDialog(self.mainwindow, gtk.DIALOG_MODAL,
                                gtk.MESSAGE_QUESTION,
                                gtk.BUTTONS_YES_NO, err);
        result = dialog.run()
        dialog.destroy()
        if result != gtk.RESPONSE_YES:
            dprint("TERMINAL: kill(); not killing")
            return True
        #self.process_manager.confirm = False
        if self.process_manager.kill_process(None, False):
            dprint("MAINWINDOW: process killed, destroying window")
            self.process_manager.window.hide()
        return False

