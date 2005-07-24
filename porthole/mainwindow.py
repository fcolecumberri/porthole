#!/usr/bin/env python
# -*- coding: UTF8 -*-

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

import threading, re #, types
import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, gtk.glade, gobject, pango
import portagelib, os, string
import utils
#from portagelib import World
World = portagelib.World
from dispatcher import Dispatcher

from gettext import gettext as _
from about import AboutDialog
from utils import dprint
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
from version_sort import ver_match
import config


EXCEPTION_LIST = ['.','^','$','*','+','?','(',')','\\','[',']','|','{','}']
SHOW_ALL = 0
SHOW_INSTALLED = 1
SHOW_SEARCH = 2
SHOW_UPGRADE = 3
ON = True
OFF = False

def check_glade():
        """determine the libglade version installed
        and return the correct glade file to use"""
        porthole_gladefile = "porthole.glade"
        #return porthole_gladefile
        # determine glade version
        versions = portagelib.get_installed("gnome-base/libglade")
        if versions:
            dprint("libglade: %s" % versions)
            old, new = ver_match(versions, ["2.0.1","2.4.9-r99"], ["2.5.0","2.99.99"])
            if old:
                dprint("MAINWINDOW: Check_glade(); Porthole no longer supports the older versions\n"+\
                        "of libglade.  Please upgrade libglade to >=2.5.0 for all GUI features to work")
                porthole_gladefile = "porthole.glade"
                new_toolbar_API = False
            elif new:
                porthole_gladefile = "porthole.glade"  # formerly "porthole-new2.glade"
                new_toolbar_API = True
        else:
            dprint("MAINWINDOW: No version list returned for libglade")
            return None
        dprint("MAINWINDOW: __init__(); glade file = %s" %porthole_gladefile)
        return porthole_gladefile, new_toolbar_API

class MainWindow:
    """Main Window class to setup and manage main window interface."""
    def __init__(self, preferences = None, config = None):
        dprint("MAINWINDOW: process id = %d ****************" %os.getpid())
        preferences.use_gladefile, self.new_toolbar_API = check_glade()
        # setup prefs
        self.prefs = preferences
        self.prefs.myarch = portagelib.get_arch()
        self.config = config
        # setup glade
        self.gladefile = self.prefs.DATA_PATH + self.prefs.use_gladefile
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
            #"on_main_window_size_request" : self.size_update,
            "on_plugin_settings_activate" : self.plugin_settings_activate,
            "on_view_refresh" : self.reload_view,
            "on_root_warning_clicked" : self.check_for_root,
            "on_configure_porthole" : self.configure_porthole,
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
        #self.wtree.get_widget("contents2").set_sensitive(False)
        # self.wtree.get_widget("btn_help").set_sensitive(False)
        # setup the category view
        self.category_view = CategoryView()
        self.category_view.register_callback(self.category_changed)
        result = self.wtree.get_widget("category_scrolled_window").add(self.category_view)
        # setup the package treeview
        self.package_view = PackageView(self.prefs)
        #self.package_view.register_callbacks(self.package_changed, None, self.pkg_path_callback)
        self.package_view.register_callbacks(self.packageview_callback)
        result = self.wtree.get_widget("package_scrolled_window").add(self.package_view)
        # setup the dependency treeview
        self.deps_view = DependsView()
        result = self.wtree.get_widget("dependencies_scrolled_window").add(self.deps_view)
        # summary view
        scroller = self.wtree.get_widget("summary_text_scrolled_window");
        self.summary = Summary(self.prefs, Dispatcher(self.summary_callback))
        result = scroller.add(self.summary)
        self.summary.show()
        # how should we setup our saved menus?
        if self.prefs.emerge.pretend:
            self.wtree.get_widget("pretend1").set_active(True)
        if self.prefs.emerge.fetch:
            self.wtree.get_widget("fetch").set_active(True)
        if self.prefs.emerge.upgradeonly :
            self.wtree.get_widget("upgradeonly").set_active(True)
        if self.prefs.emerge.verbose:
            self.wtree.get_widget("verbose4").set_active(True)
        if self.prefs.main.search_desc:
            self.wtree.get_widget("search_descriptions1").set_active(True)
        # setup a convienience tuple
        self.tool_widgets = ["emerge_package1","adv_emerge_package1","unmerge_package1","btn_emerge",
                     "btn_adv_emerge","btn_unmerge", "btn_sync", "view_refresh", "view_filter"]
        self.widget = {}
        for x in self.tool_widgets:
            self.widget[x] = self.wtree.get_widget(x)
            if not self.widget[x]:
                dprint("MAINWINDOW: __init__(); Failure to obtain widget '%s'" %x)
        # get an empty tooltip
        self.synctooltip = gtk.Tooltips()
        self.sync_tip = _(" Synchronise Package Database \n The last sync was done:\n")
        # set the sync label to the saved one set in the options
        self.widget["btn_sync"].set_label(self.prefs.globals.Sync_label)
        self.widget["view_refresh"].set_sensitive(False)
        # restore last window width/height
        if self.prefs.main.xpos and self.prefs.main.ypos:
            self.mainwindow.move(self.prefs.main.xpos, self.prefs.main.ypos)
        self.mainwindow.resize(self.prefs.main.width, self.prefs.main.height)
        # connect gtk callback for window movement and resize events
        self.mainwindow.connect("configure-event", self.size_update)
        # restore maximized state and set window-state-event handler to keep track of it
        if self.prefs.main.maximized:
            self.mainwindow.maximize()
        self.mainwindow.connect("window-state-event", self.on_window_state_event)
        # move horizontal and vertical panes
        dprint("MAINWINDOW: __init__() before hpane; %d, vpane; %d" %(self.prefs.main.hpane, self.prefs.main.vpane))
        self.hpane = self.wtree.get_widget("hpane")
        self.hpane.set_position(self.prefs.main.hpane)
        self.hpane.connect("notify", self.on_pane_notify)
        self.vpane = self.wtree.get_widget("vpane")
        self.vpane.set_position(self.prefs.main.vpane)
        self.vpane.connect("notify", self.on_pane_notify)
        # Intercept the window delete event signal
        self.mainwindow.connect('delete-event', self.confirm_delete)
        # initialize some variable to fix the hpane jump bug
        #self.hpane_bug_count = 0
        self.hpane_bug = True
        # initialize our data
        self.init_data()
        self.current_category = None
        self.current_package_name = None
        self.current_package_path = None
        self.current_search = None
        self.current_search_package_name = None
        self.current_upgrade_package_name = None
        # set if we are root or not
        self.is_root = utils.is_root()
        if self.prefs.main.show_nag_dialog:
            # let the user know if he can emerge or not
            self.check_for_root()
        if self.is_root:
            # hide warning toolbar widget
            self.wtree.get_widget("btn_root_warning").hide()
        self.toolbar_expander = self.wtree.get_widget("toolbar_expander")
        # This should be set in the glade file, but doesn't seem to work ?
        self.toolbar_expander.set_expand(True)
        # create and start our process manager
        self.process_manager = ProcessManager(utils.environment(), self.prefs, self.config, False)
        # Search History
        self.search_history = {}
        self.setup_plugins()
        dprint("MAIN: Showing main window")

    def setup_plugins(self):
        #Plugin-related statements
        self.needs_plugin_menu = False
        dprint("MAIN; setup_plugins(): path_list %s" % self.prefs.plugins.path_list)
        self.plugin_root_menu = gtk.MenuItem("Active Plugins")
        self.plugin_menu = gtk.Menu()
        self.plugin_root_menu.set_submenu(self.plugin_menu)
        self.wtree.get_widget("menubar").append(self.plugin_root_menu)
        self.plugin_manager = PluginManager( self.prefs.plugins.path_list, self )
        self.plugin_package_tabs = {}


    def init_data(self):
        # set things we can't do unless a package is selected to not sensitive
        self.set_package_actions_sensitive(False)
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
        self.db = portagelib.Database()#        self.db = None
        self.ut_running = False
        self.ut = None
        # load the db
        self.dbtime = 0
        dprint("MAINWINDOW: init_db(); starting self.db_thread")
        #self.db_thread = portagelib.DatabaseReader()
        self.db_thread = portagelib.DatabaseReader(Dispatcher(self.update_db_read))
        self.db_thread.start()
        self.db_thread_running = True
        self.reload = False
        self.upgrade_view = False
        #self.db_timeout = gobject.timeout_add(100, self.update_db_read)
        self.get_sync_time()
        self.set_sync_tip()
        # set status
        #self.set_statusbar(_("Obtaining package list "))
        self.status_root = _("Loading database")
        self.set_statusbar2(_("Initializing database. Please wait..."))
        self.progressbar = self.wtree.get_widget("progressbar1")
        self.set_cancel_btn(OFF)

    def reload_db(self, *widget):
        dprint("MAINWINDOW: reload_db() callback")
        if self.db_thread_running or self.ut_running:
            if self.db_thread_running:
                try:
                    dprint("MAINWINDOW: reload_db(); killing db thread")
                    self.db_thread.please_die()
                    self.db_thread_running = False
                except:
                    dprint("MAINWINDOW: reload_db(); failed to kill db thread")
            else: # self.ut_running
                dprint("MAINWINDOW: reload_db(); killing upgrades thread")
                self.ut.please_die()
                self.ut_running = False
            self.progress_done(True)
            # set this function to re-run after some time for the thread to stop
            self.reload_db_timeout = gobject.timeout_add(50, self.reload_db)
            return True
        # upgrades loaded?
        # reset so that it reloads the upgrade list
        #self.upgrades_loaded = False
        #self.ut_cancelled = False
        # upgrade loading callback
        self.upgrades_loaded_callback = None
        self.search_loaded = False
        self.current_package_path = None
        # test to reset portage
        #portagelib.reload_portage()
        portagelib.reload_world()
        # load the db
        self.dbtime = 0
        dprint("MAINWINDOW: reload_db(); starting self.db_thread")
        #self.db_thread = portagelib.DatabaseReader()
        self.db_thread = portagelib.DatabaseReader(Dispatcher(self.update_db_read))
        self.db_thread.start()
        self.db_thread_running = True
        #test = 87/0  # used to test pycrash is functioning
        self.reload = True
        self.upgrade_view = False
        #self.db_timeout = gobject.timeout_add(100, self.update_db_read)
        self.get_sync_time()
        self.set_sync_tip()
        # set status
        #self.set_statusbar(_("Obtaining package list "))
        self.status_root = _("Reloading database")
        self.set_statusbar2(self.status_root)
        return False

    def reload_view(self, *widget):
        """reload the package view"""
        if self.widget["view_filter"].get_history() == SHOW_UPGRADE:
            self.upgrades_loaded = False
        self.package_view.clear()
        self.set_package_actions_sensitive(False, None)
        self.category_view.populate(self.db.categories.keys())
        # update the views by calling view_filter_changed
        self.view_filter_changed(self.widget["view_filter"])
        #self.widget["view_refresh"].set_sensitive(False)
        return

    def package_update(self, pkg):
        """callback function to update an individual package
            after a successfull emerge was detected"""
        # find the pkg in self.db
        self.db.update(portagelib.extract_package(pkg))

    def sync_callback(self):
        """re-initializes portage so it uses the new metadata cache
           then init our db"""
        self.re_init_portage()
        # self.reload==False is currently broken for init_data when reloading after a sync
        #self.init_data() 
        self.reload_db()

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

    def set_sync_tip(self):
        """Sets the sync tip for the new or old toolbar API"""
        if self.new_toolbar_API:
            self.widget["btn_sync"].set_tooltip(self.synctooltip, ' '.join([self.sync_tip, self.last_sync[:-1], '']))
        else:
            self.synctooltip.set_tip(self.widget["btn_sync"], ' '.join([self.sync_tip, self.last_sync[:-1], '']))
        #self.synctooltip.enable()
        
        
    #~ def pkg_path_callback(self, path):
        #~ """callback function to save the path to the package that
        #~ matched the name passed to the populate() in PackageView"""
        #~ self.current_package_path = path
        #~ return

    def packageview_callback(self, action = None, arg = None):
        old_pretend_value = self.prefs.emerge.pretend
        if action.startswith("emerge"):
            if "pretend" in action:
                self.prefs.emerge.pretend = True
            else:
                self.prefs.emerge.pretend = False
            if "sudo" in action:
                self.emerge_package(self.package_view, sudo=True)
            else:
                self.emerge_package(self.package_view)
        elif action.startswith("unmerge"):
            self.prefs.emerge.pretend = False
            if "sudo" in action:
                self.unmerge_package(self.package_view, sudo=True)
            else:
                self.unmerge_package(self.package_view)
        elif action == "set path":
            # save the path to the package that matched the name passed
            # to populate() in PackageView... (?)
            index = self.widget["view_filter"].get_history()
            if index in [SHOW_INSTALLED, SHOW_ALL]:
                self.current_package_path = arg # arg = path
            elif index == SHOW_SEARCH:
                self.current_search_package_path = arg
            elif index == SHOW_UPGRADE:
                self.current_upgrade_package_path = arg
        elif action == "package changed":
            self.package_changed(arg)
        elif action == "refresh":
            self.refresh()
        else:
            dprint("MAINWINDOW package_view callback: unknown action '%s'" % str(action))
        self.prefs.emerge.pretend = old_pretend_value

    def summary_callback(self, action = None, arg = None):
        dprint("MAINWINDOW: summary_callback(): called")
        old_pretend_value = self.prefs.emerge.pretend
        if action.startswith("emerge"):
            ebuild = arg
            cp = portagelib.pkgsplit(ebuild)[0]
            if "pretend" in action:
                self.prefs.emerge.pretend = True
            else:
                self.prefs.emerge.pretend = False
            if "sudo" in action:
                self.setup_command( \
                    portagelib.get_name(cp),
                    ''.join(['sudo -p "Password: " emerge',
                              self.prefs.emerge.get_string(), '=', ebuild])
                )
            else:
                self.setup_command( \
                    portagelib.get_name(cp),
                    ''.join(["emerge", self.prefs.emerge.get_string(), '=', ebuild])
                )
        elif action.startswith("unmerge"):
            ebuild = arg
            cp = portagelib.pkgsplit(ebuild)[0]
            self.prefs.emerge.pretend = False
            if "sudo" in action:
                self.setup_command( \
                    portagelib.get_name(cp),
                    ''.join(['sudo -p "Password: " emerge unmerge',
                    self.prefs.emerge.get_string(), '=', ebuild])
                )
            else:
                self.setup_command(
                    portagelib.get_name(cp),
                    ''.join(["emerge unmerge", self.prefs.emerge.get_string(), '=', ebuild])
                )
        else:
            dprint("MAINWINDOW package_view callback: unknown action '%s'" % str(action))
        self.prefs.emerge.pretend = old_pretend_value

    def check_for_root(self, *args):
        """figure out if the user can emerge or not..."""
        if not self.is_root:
            self.no_root_dialog = utils.SingleButtonDialog(_("No root privileges"),
                            self.mainwindow,
                            _("In order to access all the features of Porthole,\n"
                            "please run it with root privileges."),
                            self.remove_nag_dialog,
                            _("_Ok"))

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

    def update_db_read(self, args): # extra args for dispatcher callback
        """Update the statusbar according to the number of packages read."""
        #dprint("MAINWINDOW: update_db_read()")
        #args ["nodecount", "allnodes_length","done"]
        if args["done"] == False:
            #self.dbtime += 1
            count = args["nodecount"]
            if count > 0:
                self.set_statusbar2(_("%(base)s: %(count)i packages read")
                                     % {'base':self.status_root, 'count':count})
            #dprint("self.prefs.dbtime = ")
            #dprint(self.prefs.dbtime)
            try:
                #fraction = min(1.0, max(0,(self.dbtime / float(self.prefs.dbtime))))
                fraction = min(1.0, max(0, (count / float(args["allnodes_length"]))))
                self.progressbar.set_text(str(int(fraction * 100)) + "%")
                self.progressbar.set_fraction(fraction)
            except:
                pass

        elif self.db_thread.error:
            # todo: display error dialog instead
            self.db_thread.join()
            self.set_statusbar2(self.db_thread.error.decode('ascii', 'replace'))
            return False  # disconnect from timeout
        else: # args["done"] == True - db_thread is done
            self.db_thread_running = False
            self.db_save_variables()
            self.progressbar.set_text("100%")
            self.progressbar.set_fraction(1.0)
            dprint("MAINWINDOW: db_thread is done...")
            dprint("MAINWINDOW: db_thread.join...")
            self.db_thread.join()
            self.db_thread_running = False
            dprint("MAINWINDOW: db_thread.join is done...")
            del self.db  # clean up the old db
            self.db = self.db_thread.get_db()
            self.set_statusbar2(_("%(base)s: Populating tree") % {'base':self.status_root})
            self.update_statusbar(SHOW_ALL)
            dprint("MAINWINDOW: setting menubar,toolbar,etc to sensitive...")
            for x in ["menubar","toolbar","view_filter","search_entry","btn_search","view_refresh"]:
                self.wtree.get_widget(x).set_sensitive(True)
            # make sure we search again if we reloaded!
            if self.widget["view_filter"].get_history() == SHOW_SEARCH:
                #dprint("MAINWINDOW: update_db_read()... Search view")
                # update the views by calling view_filter_changed
                self.view_filter_changed(self.widget["view_filter"])
                # reset the upgrades list if it is loaded and not being viewed
                self.upgrades_loaded = False
                if self.reload:
                    # reset _last_selected so it thinks this package is new again
                    self.package_view._last_selected = None
                    if self.current_search_package_cursor != None \
                            and self.current_search_package_cursor[0]: # should fix a type error in set_cursor; from pycrash report
                        # re-select the package
                        self.package_view.set_cursor(self.current_search_package_cursor[0],
                                                     self.current_search_package_cursor[1])
            elif self.reload and (self.widget["view_filter"].get_history() == SHOW_ALL or \
                                  self.widget["view_filter"].get_history() == SHOW_INSTALLED):
                #dprint("MAINWINDOW: update_db_read()... self.reload=True ALL or INSTALLED view")
                # reset _last_selected so it thinks this category is new again
                self.category_view._last_category = None
                #dprint("MAINWINDOW: re-select the category: self.current_category_cursor =")
                #dprint(self.current_category_cursor)
                #dprint(type(self.current_category_cursor))
                if (self.current_category_cursor != None) and (self.current_category_cursor != [None,None]):
                    # re-select the category
                    try:
                        self.category_view.set_cursor(self.current_category_cursor[0],
                                                      self.current_category_cursor[1])
                    except:
                        dprint("MAINWINDOW: update_db_read(); error converting self.current_category_cursor[]: %s"
                                %str(self.current_category_cursor))
                #~ #dprint("MAINWINDOW: reset _last_selected so it thinks this package is new again")
                # reset _last_selected so it thinks this package is new again
                self.package_view._last_selected = None
                #~ #dprint("MAINWINDOW: re-select the package")
                # re-select the package
                if self.current_package_path != None:
                    if self.current_package_cursor != None and self.current_package_cursor[0]:
                        self.package_view.set_cursor(self.current_package_path,
                                                     self.current_package_cursor[1])
                self.view_filter_changed(self.widget["view_filter"])
                # reset the upgrades list if it is loaded and not being viewed
                self.upgrades_loaded = False
            else:
                if self.reload:
                    #dprint("MAINWINDOW: update_db_read()... must be an upgradeable view")
                    self.widget['view_refresh'].set_sensitive(True)
                    ## hmm, don't mess with upgrade list after an emerge finishes.
                else:
                    self.reload_view()
            dprint("MAINWINDOW: Made it thru a reload, returning...")
            self.progress_done(False)
            #if not self.reload:
            #self.view_filter_changed(self.widget["view_filter"])
            self.reload = False
            return False  # disconnect from timeout
        #dprint("MAINWINDOW: returning from update_db_read() count=%d dbtime=%d"  %(count, self.dbtime))
        return True

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


    def setup_command(self, package_name, command, run_anyway=False):
        """Setup the command to run or not"""
        if (self.is_root
                or run_anyway
                or (self.prefs.emerge.pretend and command[:11] != self.prefs.globals.Sync)
                or command.startswith("sudo")):
            if self.prefs.emerge.pretend or utils.pretend_check(command) or utils.help_check(command)\
                or utils.info_check(command):
                # temp set callback for testing
                callback = self.sync_callback #lambda: None  # a function that does nothing
            elif package_name == "Sync Portage Tree":
                callback = self.sync_callback #self.init_data
            else:
                callback = self.reload_db
                #callback = self.package_update
            #ProcessWindow(command, env, self.prefs, callback)
            self.process_manager.add_process(package_name, command, callback)
        else:
            dprint("MAINWINDOW: Must be root user to run command '%s' " % command)
            #self.sorry_dialog = utils.SingleButtonDialog(_("You are not root!"),
            #        self.mainwindow,
            #        _("Please run Porthole as root to emerge packages!"),
            #        None, "_Ok")
            self.check_for_root() # displays not root dialog
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
        if hasattr(self, "widget") and self.widget["view_filter"].get_history() == SHOW_UPGRADE:
            if self.ut_running: # aargh, kill it
                self.ut.please_die()
                dprint("MAINWINDOW: joining upgrade thread...")
                self.ut.join()
                dprint("MAINWINDOW: finished!")
                self.ut_running = False
            #dprint("MAINWINDOW: upgradeonly_set()...reload upgradeable view")
            self.package_view.clear()
            self.set_package_actions_sensitive(False, None)
            # update the views by calling view_filter_changed
            self.view_filter_changed(self.widget["view_filter"])
            self.reload_view(None)

    def search_set(self, widget):
        """Set whether or not to search descriptions"""
        self.prefs.main.search_desc = widget.get_active()

    def emerge_package(self, widget, sudo=False):
        """Emerge the currently selected package."""
        package = utils.get_treeview_selection(self.package_view, 2)
        if (sudo or (not utils.is_root() and utils.can_sudo())) \
                and not self.prefs.emerge.pretend:
            self.setup_command(package.get_name(), 'sudo -p "Password: " emerge' +
                self.prefs.emerge.get_string() + package.full_name)
        else:
            self.setup_command(package.get_name(), "emerge" +
                self.prefs.emerge.get_string() + package.full_name)

    def adv_emerge_package(self, widget):
        """Advanced emerge of the currently selected package."""
        package = utils.get_treeview_selection(self.package_view, 2)
        # Activate the advanced emerge dialog window
        dialog = AdvancedEmergeDialog(self.prefs, package, self.setup_command)

    def new_plugin_package_tab( self, name, callback, widget ):
        notebook = self.wtree.get_widget("notebook")
        label = gtk.Label(name)
        notebook.append_page(widget, label)
        page_num = notebook.page_num(widget)
        self.plugin_package_tabs[name] = [callback, label, page_num]

    def del_plugin_package_tab( self, name ):
        notebook = self.wtree.get_widget("notebook")
        notebook.remove_page(self.plugin_package_tabs[name][1])
        self.plugin_package_tabs.remove(name)

    def plugin_settings_activate( self, widget ):
        """Shows the plugin settings window"""
        plugin_dialog = PluginGUI( self.prefs, self.plugin_manager )
    
    def configure_porthole(self, menuitem_widget):
        """Shows the Configuration GUI"""
        config_dialog = config.ConfigDialog(self.prefs)
    
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

    def unmerge_package(self, widget, sudo=False):
        """Unmerge the currently selected package."""
        package = utils.get_treeview_selection(self.package_view, 2)
        if (sudo or (not utils.is_root() and utils.can_sudo())) \
                and not self.prefs.emerge.pretend:
            self.setup_command(package.get_name(), 'sudo -p "Password: " emerge unmerge' +
                    self.prefs.emerge.get_string() + package.full_name)
        else:
            self.setup_command(package.get_name(), "emerge unmerge" +
                    self.prefs.emerge.get_string() + package.full_name)

    def sync_tree(self, widget):
        """Sync the portage tree and reload it when done."""
        sync = self.prefs.globals.Sync
        if self.prefs.emerge.verbose:
            sync += " --verbose"
        if self.prefs.emerge.nospinner:
            sync += " --nospinner "
        if utils.is_root():
            self.setup_command("Sync Portage Tree", sync)
        elif utils.can_sudo():
            self.setup_command("Sync Portage Tree", 'sudo -p "Password: " ' + sync)
        else:
            self.check_for_root()

    def on_cancel_btn(self, widget):
        """cancel button callback function"""
        dprint("MAINWINDOW: on_cancel_btn() callback")
        # terminate the thread
        self.ut.please_die()
        self.ut.join()
        self.progress_done(True)

    def on_window_state_event(self, widget, event):
        """Handler for window-state-event gtk callback.
        Just checks if the window is maximized or not"""
        if widget is not self.mainwindow: return False
        dprint("MAINWINDOW: on_window_state_event(); event detected")
        if gtk.gdk.WINDOW_STATE_MAXIMIZED & event.new_window_state:
            self.prefs.main.maximized = True
        else:
            self.prefs.main.maximized = False
    
    def on_pane_notify(self, pane, gparamspec):
        if gparamspec.name == "position":
            # bugfix for hpane jump bug. Now why does this happen?
            # it seems we need to reset the hpane the first time this gets called...
            if self.hpane_bug:
                self.hpane.set_position(self.prefs.main.hpane)
                self.hpane_bug = False
                return True
            # save hpane, vpane positions
            self.prefs.main.hpane = hpanepos = self.hpane.get_position()
            self.prefs.main.vpane = vpanepos = self.vpane.get_position()
            dprint("MAINWINDOW on_pane_notify(): saved hpane %(hpanepos)s, vpane %(vpanepos)s" % locals())
    
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
                        if not self.setup_command(key, "emerge --oneshot --noreplace" +
                                self.prefs.emerge.get_string() + key[:]): #use the full name
                            return
                elif not self.setup_command(key, "emerge --noreplace" +
                                self.prefs.emerge.get_string() + ' ' + key[:]): #use the full name
                    return
        else:
            dprint("MAIN: Upgrades not loaded; upgrade world?")
            self.upgrades_loaded_dialog = utils.YesNoDialog(_("Upgrade requested"),
                    self.mainwindow,
                    _("Do you want to upgrade all packages in your world file?"),
                     self.upgrades_loaded_dialog_response)

    def tree_node_to_list(self, model, path, iter):
        """callback function from gtk.TreeModel.foreach(),
           used to add packages to an upgrades list"""
        if model.get_value(iter, 1):
            name = model.get_value(iter, 0)
            dprint("MAINWINDOW; tree_node_to_list(): name '%s'" % name)
            if name not in self.keyorder:
                self.packages_list[name] = model.get_value(iter, 4) # model.get_value(iter, 2), name]
                self.keyorder = [name] + self.keyorder 
        return False


    def upgrades_loaded_dialog_response(self, widget, response):
        """ Get and parse user's response """
        if response == 0: # Yes was selected; upgrade all
            #self.load_upgrades_list()
            #self.upgrades_loaded_callback = self.upgrade_packages
            if not utils.is_root() and utils.can_sudo() \
                    and not self.prefs.emerge.pretend:
                self.setup_command('world', 'sudo -p "Password: " emerge --update' +
                        self.prefs.emerge.get_string() + 'world')
            else:
                self.setup_command('world', "emerge --update" +
                        self.prefs.emerge.get_string() + 'world')
        else:
            # load the upgrades view to select which packages
            self.widget["view_filter"].set_history(SHOW_UPGRADE)
        # get rid of the dialog
        self.upgrades_loaded_dialog.destroy()

    def load_descriptions_list(self):
        """ Load a list of all descriptions for searching """
        self.desc_dialog = utils.SingleButtonDialog(_("Please Wait!"),
                self.mainwindow,
                _("Loading package descriptions..."),
                self.desc_dialog_response, "_Cancel", True)
        dprint("MAINWINDOW: load_descriptions_list(); starting self.desc_thread")
        self.desc_thread = DescriptionReader(self.db.list)
        self.desc_thread.start()
        gobject.timeout_add(100, self.desc_thread_update)

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
            return False
        else:
            # print self.desc_thread.count
            if self.db:
                fraction = self.desc_thread.count / float(len(self.db.list))
                self.desc_dialog.progbar.set_text(str(int(fraction * 100)) + "%")
                self.desc_dialog.progbar.set_fraction(fraction)
        return True

    def package_search(self, widget=None):
        """Search package db with a string and display results."""
        self.clear_notebook()
        if not self.desc_loaded and self.prefs.main.search_desc:
            self.load_descriptions_list()
            return
        tmp_search_term = self.wtree.get_widget("search_entry").get_text()
        #dprint(tmp_search_term)
        if tmp_search_term:
            # change view and statusbar so user knows it's searching.
            # This won't actually do anything unless we thread the search.
            self.widget["view_filter"].set_history(SHOW_SEARCH)
            self.search_loaded = True # or else v_f_c() tries to call package_search again
            self.view_filter_changed(self.widget["view_filter"])
            if self.prefs.main.search_desc:
                self.set_statusbar2(_("Searching descriptions for %s") % tmp_search_term)
            else:
                self.set_statusbar2(_("Searching for %s") % tmp_search_term)
            search_term = ''
            Plus_exeption_count = 0
            for char in tmp_search_term:
                #dprint(char)
                if char in EXCEPTION_LIST:# =="+":
                    dprint("MAINWINDOW: package_search()  '%s' exception found" %char)
                    char = "\\" + char
                search_term += char 
            dprint("MAINWINDOW: package_search() ===> escaped search_term = :%s" %search_term)
            #switch to search view in the package_view
            search_results = self.package_view.search_model
            search_results.clear()
            re_object = re.compile(search_term, re.I)
            count = 0
            package_list = {}
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
                    #dprint("MAINWINDOW: package_search; found: %s, in_world=%d" %(data.full_name,data.in_world))
                    search_results.set_value(iter, 4, data.in_world)
                    search_results.set_value(iter, 6, data.get_size())
                    installed = data.get_latest_installed()
                    latest = data.get_latest_ebuild()
                    try:
                        installed = portagelib.get_version( installed )
                    except IndexError:
                        installed = ""
                    try:
                        latest = portagelib.get_version( latest )
                    except IndexError:
                        latest = "Error"
                    search_results.set_value(iter, 7, installed)
                    search_results.set_value(iter, 8, latest)
                    search_results.set_value(iter, 9, data.get_properties().description )

                    # set the icon depending on the status of the package
                    icon = utils.get_icon_for_package(data)
                    view = self.package_view
                    search_results.set_value(
                        iter, 3,
                        view.render_icon(icon,
                                         size = gtk.ICON_SIZE_MENU,
                                         detail = None))
                    package_list[name] = data
            search_results.size = count  # store number of matches
            # in case the search view was already active
            self.update_statusbar(SHOW_SEARCH)
            self.search_history[search_term] = package_list
            #Add the current search_results to the top of the category view
            self.category_view.populate(self.search_history.keys())
            iter = self.category_view.model.get_iter_first()
            while iter != None:
                if self.category_view.model.get_value(iter, 1) == search_term:
                    selection = self.category_view.get_selection()
                    selection.select_iter(iter)
                    break
                iter = self.category_view.model.iter_next(iter)
            if count == 1: # then select it
                self.current_search_package_name = package_list.keys()[0]
            self.category_view.last_category = search_term
            self.category_changed(search_term)

    def help_contents(self, widget):
        """Show the help file contents."""
        load_web_page('file://' + self.prefs.DATA_PATH + 'help/index.html', self.prefs)

    def about(self, widget):
        """Show about dialog."""
        dialog = AboutDialog(self.prefs)

    def refresh(self):
        """Refresh PackageView"""
        if mode == SHOW_SEARCH:
            self.category_changed(self.current_search)
        else:
            self.category_changed(self.current_category)

    def category_changed(self, category):
        """Catch when the user changes categories."""
        mode = self.widget["view_filter"].get_history()
        # log the new category for reloads
        if mode != SHOW_SEARCH:
            self.current_category = category
            self.current_category_cursor = self.category_view.get_cursor()
        else:
            self.current_search = category
            self.current_search_cursor = self.category_view.get_cursor()
        if not self.reload:
            self.current_package_cursor = None
        #dprint("Category cursor = " +str(self.current_category_cursor))
        #dprint(self.current_category_cursor[0][1])
        self.clear_notebook()
        if mode == SHOW_SEARCH:
            packages = self.search_history[category]
            #if len(packages) == 1: # then select it
            #    self.current_search_package_name = packages.values()[0].get_name()
            #self.package_view.populate(packages, self.current_search_package_name)
            # if search was a package name, select that one
            # (searching for 'python' for example would benefit)
            self.package_view.populate(packages, category)
        elif not category or self.current_category_cursor[0][1] == None:
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
            self.package_view.populate(packages, self.current_package_name)
        elif mode == SHOW_INSTALLED:
            packages = self.db.installed[category]
            self.package_view.populate(packages, self.current_package_name)
        else:
            raise Exception("The programmer is stupid.");

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
        index = self.widget["view_filter"].get_history()
        if index in [SHOW_INSTALLED, SHOW_ALL]:
            self.current_package_name = package.get_name()
            self.current_package_cursor = self.package_view.get_cursor()
            self.current_package_path = self.current_package_cursor[0]
        elif index == SHOW_SEARCH:
            self.current_search_package_name = package.get_name()
            self.current_search_package_cursor = self.package_view.get_cursor()
            self.current_search_package_path = self.current_search_package_cursor[0]
        elif index == SHOW_UPGRADE:
            self.current_upgrade_package_name = package.get_name()
            self.current_upgrade_package_cursor = self.package_view.get_cursor()
            self.current_upgrade_package_path = self.current_upgrade_package_cursor[0]
        #dprint("Package name= %s, cursor = " %str(self.current_package_name))
        #dprint(self.current_package_cursor)
        # the notebook must be sensitive before anything is displayed
        # in the tabs, especially the deps_view
        self.set_package_actions_sensitive(True, package)
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
        else:
            for i in self.plugin_package_tabs:
                #Search through the plugins dictionary and select the correct one.
                if self.plugin_package_tabs[i][2] == cur_page:
                    self.plugin_package_tabs[i][0]( package )

    def notebook_changed(self, widget, pointer, index):
        """Catch when the user changes the notebook"""
        package = utils.get_treeview_selection(self.package_view, 2)
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
            else:
                for i in self.plugin_package_tabs:
                    #Search through the plugins dictionary and select the correct one.
                    if self.plugin_package_tabs[i][2] == index:
                        self.plugin_package_tabs[i][0]( package )

    def view_filter_changed(self, widget):
        """Update the treeviews for the selected filter"""
        dprint("MAINWINDOW: view_filter_changed()")
        index = widget.get_history()
        dprint("MAINWINDOW: view_filter_changed(); index = %d" %index)
        self.update_statusbar(index)
        cat_scroll = self.wtree.get_widget("category_scrolled_window")
        self.category_view.set_search(False)
        self.clear_notebook()
        if index in (SHOW_INSTALLED, SHOW_ALL):
            cat_scroll.show();
            self.category_view.populate( \
                index == SHOW_ALL and self.db.categories.keys()
                or self.db.installed.keys())
            self.package_view.set_view(self.package_view.PACKAGES)
            self.package_view._init_view()
            self.package_view.clear()
            cat = self.current_category
            pack = self.current_package_name
            self.select_category_package(cat, pack, index)
        elif index == SHOW_SEARCH:
            self.category_view.set_search(True)
            if not self.search_loaded:
                self.set_package_actions_sensitive(False, None)
                self.category_view.populate(self.search_history.keys())
                self.package_search(None)
                self.search_loaded = True
            self.category_view.populate(self.search_history.keys())
            cat_scroll.show();
            dprint("MAIN: Showing search results")
            self.package_view.set_view(self.package_view.SEARCH_RESULTS)
            cat = self.current_search
            pack = self.current_search_package_name
            self.select_category_package(cat, pack, index)
        elif index == SHOW_UPGRADE:
            dprint("MAINWINDOW: view_filter_changed(); upgrade selected")
            cat_scroll.hide();
            self.package_view.set_view(self.package_view.UPGRADABLE)
            if not self.upgrades_loaded:
                dprint("MAINWINDOW: view_filter_changed(); calling load_upgrades_list ********************************")
                self.load_upgrades_list()
                self.package_view.clear()
                dprint("MAINWINDOW: view_filter_changed(); back from load_upgrades_list()")
            else:
                # already loaded, just show them!
                dprint("MAINWINDOW: view_filter_changed(); showing loaded upgrades")
                #self.package_view.set_view(self.package_view.UPGRADABLE)
                self.summary.update_package_info(None)
        # clear the notebook tabs
        #self.clear_notebook()
        #if self.last_view_setting != index:
        dprint("MAINWINDOW: view_filter_changed(); last_view_setting changed")
        self.last_view_setting = index
        #self.current_category = None
        #self.category_view.last_category = None
        #self.current_category_cursor = None
        #self.current_package_cursor = None
    
    def select_category_package(self, cat, pack, index):
        dprint("MAINWINDOW: select_category_package(): %s / %s" % (cat, pack))
        model = self.category_view.get_model()
        iter = model.get_iter_first()
        catpath = None
        if index in [SHOW_INSTALLED, SHOW_ALL] and cat and '-' in cat:
            # find path of category
            catmaj, catmin = cat.split("-")
            #dprint("catmaj, catmin = %s, %s" % (catmaj, catmin))
            while iter:
                #dprint("value at iter %s: %s" % (iter, model.get_value(iter, 0)))
                if catmaj == model.get_value(iter, 0):
                    kids = model.iter_n_children(iter)
                    while kids: # this will count backwards, but hey so what
                        kiditer = model.iter_nth_child(iter, kids - 1)
                        if catmin == model.get_value(kiditer, 0):
                            catpath = model.get_path(kiditer)
                            break
                        kids -= 1
                    if catpath: break
                iter = model.iter_next(iter)
        elif index == SHOW_SEARCH:
            while iter:
                if cat == model.get_value(iter, 0):
                    catpath = model.get_path(iter)
                    break
                iter = model.iter_next(iter)
        elif index == SHOW_UPGRADE:
            catpath = 'Sure, why not?'
        else: dprint("MAINWINDOW: select_category_package(): bad index or category?")
        if catpath:
            if index != SHOW_UPGRADE:
                self.category_view.expand_to_path(catpath)
                self.category_view.last_category = None # so it thinks it's changed
                self.category_view.set_cursor(catpath)
            # now reselect whatever package we had selected
            model = self.package_view.get_model()
            iter = model.get_iter_first()
            path = None
            while iter:
                #dprint("value at iter %s: %s" % (iter, model.get_value(iter, 0)))
                if model.get_value(iter, 0) == pack:
                    path = model.get_path(iter)
                    self.package_view._last_selected = None
                    self.package_view.set_cursor(path)
                    break
                iter = model.iter_next(iter)
            if not path:
                dprint("MAINWINDOW: select_category_package(): no package found")
                self.clear_notebook()
        else:
            dprint("MAINWINDOW: select_category_package(): no category path found")
            self.clear_notebook()

    def load_upgrades_list(self):
        # upgrades are not loaded, create dialog and load them
        self.set_statusbar2(_("Searching for upgradable packages..."))
        # create upgrade thread for loading the upgrades
        #self.ut = UpgradableReader(Dispatcher(self.Update_upgrades, self.package_view, self.db.installed.items(),
        #                           self.prefs.emerge.upgradeonly, self.prefs.views ))
        if self.ut_running:
            dprint("MAINWINDOW: load_upgrades_list(); upgrades thread already running!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return
        dprint("MAINWINDOW: load_upgrades_list(); starting upgrades thread")
        self.ut = UpgradableReader(self.package_view, self.db.installed.items(),
                                   self.prefs.emerge.upgradeonly, self.prefs.views )
        self.ut.start()
        self.ut_running = True
        self.build_deps = False
        # add a timeout to check if thread is done
        gobject.timeout_add(200, self.update_upgrade_thread)
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
            self.ut.join()
            self.ut_running = False
            self.progress_done(True)
            if self.ut.cancelled:
                return False
            self.upgrades_loaded = True
            self.view_filter_changed(self.widget["view_filter"])
            if self.upgrades_loaded_callback:
                self.upgrades_loaded_callback(None)
                self.upgrades_loaded_callback = None
            else:
                if self.last_view_setting == SHOW_UPGRADE:
                    self.package_view.set_view(self.package_view.UPGRADABLE)
                    self.summary.update_package_info(None)
                    #self.wtree.get_widget("category_scrolled_window").hide()
            return False
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
                            self.set_statusbar2(_("Building Package List"))
                except Exception, e:
                    dprint("MAINWINDOW: update_upgrade_thread(): Exception: %s" % e)
        return True

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
                text = (_("%(pack)d packages in %(cat)d categories")
                        % {'pack':len(self.db.list), 'cat':len(self.db.categories)})
        elif mode == SHOW_INSTALLED:
            if not self.db:
                dprint("MAINWINDOW: attempt to update status bar with no db assigned")
            else:
                text = (_("%(pack)d packages in %(cat)d categories") 
                        % {'pack':self.db.installed_count, 'cat':len(self.db.installed)})
        elif mode == SHOW_SEARCH:
            text = (_("%d matches found") % self.package_view.search_model.size)

        elif mode == SHOW_UPGRADE:
            if not self.ut:
                dprint("MAINWINDOW: attempt to update status bar with no upgrade thread assigned")
            else:
                text = (_("%(world)d world, %(deps)d dependencies")
                            % {'world':self.ut.world_count, 'deps':self.ut.dep_count})

        self.set_statusbar2(self.status_root + text)

    def set_package_actions_sensitive(self, enabled, package = None):
        """Sets package action buttons/menu items to sensitive or not"""
        #dprint("MAINWINDOW: set_package_actions_sensitive(%d)" %enabled)
        self.widget["emerge_package1"].set_sensitive(enabled)
        self.widget["adv_emerge_package1"].set_sensitive(enabled)
        self.widget["unmerge_package1"].set_sensitive(enabled)
        self.widget["btn_emerge"].set_sensitive(enabled)
        self.widget["btn_adv_emerge"].set_sensitive(enabled)
        if not enabled or enabled and package.get_installed():
            #dprint("MAINWINDOW: set_package_actions_sensitive() setting unmerge to %d" %enabled)
            self.widget["btn_unmerge"].set_sensitive(enabled)
            self.widget["unmerge_package1"].set_sensitive(enabled)
        else:
            #dprint("MAINWINDOW: set_package_actions_sensitive() setting unmerge to %d" %(not enabled))
            self.widget["btn_unmerge"].set_sensitive(not enabled)
            
            self.widget["unmerge_package1"].set_sensitive(not enabled)
        self.notebook.set_sensitive(enabled)

    def size_update(self, widget, event):
        #dprint("MAINWINDOW: size_update(); called.")
        """ Store the window and pane positions """
        self.prefs.main.width = event.width
        self.prefs.main.height = event.height
        pos = widget.get_position()
        # note: event has x and y attributes but they do not give the same values as get_position().
        self.prefs.main.xpos = pos[0]
        self.prefs.main.ypos = pos[1]

    def clear_notebook(self):
        """ Clear all notebook tabs & disable them """
        #dprint("MAINWINDOW: clear_notebook()")
        self.summary.update_package_info(None)
        self.set_package_actions_sensitive(False)
        self.deps_view.clear()
        self.changelog.set_text('')
        self.installed_files.set_text('')
        self.ebuild.set_text('')

    def open_log(self, widget):
        """ Open a log of a previous emerge in a new terminal window """
        newterm = ProcessManager(utils.environment(), self.prefs, self.config, True)
        newterm.do_open(widget)

    def custom_run(self, widget):
        """ Run a custom command in the terminal window """
        #dprint("MAINWINDOW: entering custom_run")
        #dprint(self.prefs.run_dialog.history)
        get_command = RunDialog(self.prefs, self.setup_command, run_anyway=True)

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
            self.process_manager.allow_delete = True
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
            self.process_manager.allow_delete = True
            self.process_manager.window.hide()
        return False

