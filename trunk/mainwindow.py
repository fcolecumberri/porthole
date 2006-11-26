#!/usr/bin/env python
# -*- coding: UTF8 -*-

'''
    Porthole Main Window
    The main interface the user will interact with

    Copyright (C) 2003 - 2006
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

import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, gtk.glade, gobject
import os
from gettext import gettext as _

import utils.utils, utils.debug

import config
import backends
portage_lib = backends.portage_lib

World = portage_lib.World

from utils.dispatcher import Dispatcher
from dialogs.about import AboutDialog
from dialogs.command import RunDialog
from dialogs.simple import SingleButtonDialog, YesNoDialog
from dialogs.configure import ConfigDialog
from packagebook.notebook import PackageNotebook
from packagebook.depends import DependsTree
from terminal.terminal import ProcessManager
from views.category import CategoryView
from views.package import PackageView
from views.depends import DependsView
from views.commontreeview import CommonTreeView
from advancedemerge.advemerge import AdvancedEmergeDialog
from plugin import PluginGUI, PluginManager
from readers.upgradeables import UpgradableListReader
from readers.descriptions import DescriptionReader
from readers.search import SearchReader
from loaders.loaders import *
from backends.version_sort import ver_match
from backends.utilities import get_sync_info
import db
#from timeit import Timer


SHOW_ALL = 0
SHOW_INSTALLED = 1
SHOW_SEARCH = 2
SHOW_UPGRADE = 3
SHOW_REBUILD = 4
ON = True
OFF = False

def check_glade():
        """determine the libglade version installed
        and return the correct glade file to use"""
        porthole_gladefile = "porthole.glade"
        #return porthole_gladefile
        # determine glade version
        versions = portage_lib.get_installed("gnome-base/libglade")
        if versions:
            utils.debug.dprint("libglade: %s" % versions)
            old, new = ver_match(versions, ["2.0.1","2.4.9-r99"], ["2.5.0","2.99.99"])
            if old:
                utils.debug.dprint("MAINWINDOW: Check_glade(); Porthole no longer supports the older versions\n"+\
                        "of libglade.  Please upgrade libglade to >=2.5.0 for all GUI features to work")
                porthole_gladefile = "porthole.glade"
                new_toolbar_API = False
            elif new:
                porthole_gladefile = "porthole.glade"  # formerly "porthole-new2.glade"
                new_toolbar_API = True
        else:
            utils.debug.dprint("MAINWINDOW: No version list returned for libglade")
            return None, None
        utils.debug.dprint("MAINWINDOW: __init__(); glade file = %s" %porthole_gladefile)
        return porthole_gladefile, new_toolbar_API

class MainWindow:
    """Main Window class to setup and manage main window interface."""
    def __init__(self) :#, preferences = None, configs = None):
        utils.debug.dprint("MAINWINDOW: process id = %d ****************" %os.getpid())
        config.Prefs.use_gladefile, self.new_toolbar_API = check_glade()
        # setup prefs
        config.Prefs.myarch = portage_lib.get_arch()
        utils.debug.dprint("MAINWINDOW: Prefs.myarch = " + config.Prefs.myarch)
        #self.config = configs
        # setup glade
        self.gladefile = config.Prefs.DATA_PATH + config.Prefs.use_gladefile
        self.wtree = gtk.glade.XML(self.gladefile, "main_window", config.Prefs.APP)
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
        callbacks = {
            "summary_callback" : self.summary_callback,
            "re_init_portage" : self.re_init_portage,
            "set_package_actions_sensitive" : self.set_package_actions_sensitive
        }
        # initialize this now cause we need it next
        self.plugin_package_tabs = {}
        # create the primary package notebook
        self.packagebook = PackageNotebook(self.wtree, callbacks, self.plugin_package_tabs)
        # set unfinished items to not be sensitive
        #self.wtree.get_widget("contents2").set_sensitive(False)
        # self.wtree.get_widget("btn_help").set_sensitive(False)
        # setup the category view
        self.category_view = CategoryView()
        self.category_view.register_callback(self.category_changed)
        result = self.wtree.get_widget("category_scrolled_window").add(self.category_view)
        # setup the package treeview
        self.package_view = PackageView()
        #self.package_view.register_callbacks(self.package_changed, None, self.pkg_path_callback)
        self.package_view.register_callbacks(self.packageview_callback)
        result = self.wtree.get_widget("package_scrolled_window").add(self.package_view)
        # how should we setup our saved menus?
        if config.Prefs.emerge.pretend:
            self.wtree.get_widget("pretend1").set_active(True)
        if config.Prefs.emerge.fetch:
            self.wtree.get_widget("fetch").set_active(True)
        if config.Prefs.emerge.upgradeonly :
            self.wtree.get_widget("upgradeonly").set_active(True)
        if config.Prefs.emerge.verbose:
            self.wtree.get_widget("verbose4").set_active(True)
        if config.Prefs.main.search_desc:
            self.wtree.get_widget("search_descriptions1").set_active(True)
        # setup a convienience tuple
        self.tool_widgets = ["emerge_package1","adv_emerge_package1","unmerge_package1","btn_emerge",
                     "btn_adv_emerge","btn_unmerge", "btn_sync", "view_refresh", "view_filter"]
        self.widget = {}
        for x in self.tool_widgets:
            self.widget[x] = self.wtree.get_widget(x)
            if not self.widget[x]:
                utils.debug.dprint("MAINWINDOW: __init__(); Failure to obtain widget '%s'" %x)
        # get an empty tooltip
        self.synctooltip = gtk.Tooltips()
        self.sync_tip = _(" Synchronise Package Database \n The last sync was done:\n")
        # set the sync label to the saved one set in the options
        self.widget["btn_sync"].set_label(config.Prefs.globals.Sync_label)
        self.widget["view_refresh"].set_sensitive(False)
        # restore last window width/height
        if config.Prefs.main.xpos and config.Prefs.main.ypos:
            self.mainwindow.move(config.Prefs.main.xpos, config.Prefs.main.ypos)
        self.mainwindow.resize(config.Prefs.main.width, config.Prefs.main.height)
        # connect gtk callback for window movement and resize events
        self.mainwindow.connect("configure-event", self.size_update)
        # restore maximized state and set window-state-event handler to keep track of it
        if config.Prefs.main.maximized:
            self.mainwindow.maximize()
        self.mainwindow.connect("window-state-event", self.on_window_state_event)
        # move horizontal and vertical panes
        #utils.debug.dprint("MAINWINDOW: __init__() before hpane; %d, vpane; %d" %(config.Prefs.main.hpane, config.Prefs.main.vpane))
        self.hpane = self.wtree.get_widget("hpane")
        self.hpane.set_position(config.Prefs.main.hpane)
        self.hpane.connect("notify", self.on_pane_notify)
        self.vpane = self.wtree.get_widget("vpane")
        self.vpane.set_position(config.Prefs.main.vpane)
        self.vpane.connect("notify", self.on_pane_notify)
        # Intercept the window delete event signal
        self.mainwindow.connect('delete-event', self.confirm_delete)
        # initialize some variable to fix the hpane jump bug
        #self.hpane_bug_count = 0
        self.hpane_bug = True
        # initialize now so that the update_db_callback doesn't puke
        self.plugin_manager = None
        self.plugin_package_tabs = {}
        # initialize our data
        self.init_data()
        # set if we are root or not
        self.is_root = utils.utils.is_root()
        if config.Prefs.main.show_nag_dialog:
            # let the user know if he can emerge or not
            self.check_for_root()
        if self.is_root:
            # hide warning toolbar widget
            self.wtree.get_widget("btn_root_warning").hide()
        self.toolbar_expander = self.wtree.get_widget("toolbar_expander")
        # This should be set in the glade file, but doesn't seem to work ?
        self.toolbar_expander.set_expand(True)
        # create and start our process manager
        self.process_manager = ProcessManager(utils.utils.environment(), False)
        # Search History
        self.search_history = {}
        self.search_history_counts = {}
        self.setup_plugins()
        utils.debug.dprint("MAINWINDOW: Showing main window")
        self.mainwindow.show_all()

    def setup_plugins(self):
        #Plugin-related statements
        self.needs_plugin_menu = False
        #utils.debug.dprint("MAIN; setup_plugins(): path_list %s" % config.Prefs.plugins.path_list)
        utils.debug.dprint("MAIN: setup_plugins: plugin path: %s" % config.Prefs.PLUGIN_DIR)
        self.plugin_root_menu = gtk.MenuItem(_("Active Plugins"))
        self.plugin_menu = gtk.Menu()
        self.plugin_root_menu.set_submenu(self.plugin_menu)
        self.wtree.get_widget("menubar").append(self.plugin_root_menu)
        self.plugin_manager = PluginManager(self)
        self.plugin_package_tabs = {}

    def init_data(self):
        # set things we can't do unless a package is selected to not sensitive
        self.set_package_actions_sensitive(False)
        utils.debug.dprint("MAINWINDOW: init_data(); Initializing data")
        # set status
        #self.set_statusbar(_("Obtaining package list "))
        self.status_root = _("Loading database")
        self.set_statusbar2(_("Initializing database. Please wait..."))
        self.progressbar = self.wtree.get_widget("progressbar1")
        self.set_cancel_btn(OFF)
        db.db.set_callback(self.update_db_read)
        # upgrades loaded?
        self.upgrades_loaded = False
        # upgrade loading callback
        self.upgrades_loaded_callback = None
        self.upgrades = {}
        self.current_package_cursor = None
        self.current_category_cursor = None
        self.current_category = None
        self.current_package_name = None
        self.current_package_path = None
        self.current_search = None
        self.current_search_package_name = None
        self.current_upgrade_package_name = None
        self.current_upgrade_category = None
        # descriptions loaded?
        #self.desc_loaded = False
        self.search_loaded = False
        self.current_package_path = None
        # view filter setting
        self.last_view_setting = None
        # set notebook tabs to load new package info
        self.packagebook.reset_tabs()
        self.ut_running = False
        self.ut = None
        # load the db
        #utils.debug.dprint("MAINWINDOW: init_db(); starting db.db.db_thread")
        self.reload = False
        self.upgrade_view = False
        #self.db_timeout = gobject.timeout_add(100, self.update_db_read)
        self.last_sync = _("Unknown")
        self.get_sync_time()
        self.set_sync_tip()

    def reload_db(self, *widget):
        utils.debug.dprint("MAINWINDOW: reload_db() callback")
        if db.db.db_thread_running or self.ut_running:
            if db.db.db_thread_running:
                try:
                    utils.debug.dprint("MAINWINDOW: reload_db(); killing db thread")
                    db.db.db_thread_cancell()
                except:
                    utils.debug.dprint("MAINWINDOW: reload_db(); failed to kill db thread")
            else: # self.ut_running
                utils.debug.dprint("MAINWINDOW: reload_db(); killing upgrades thread")
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
        #self.upgrades_loaded_callback = None
        #self.upgrades = {}
        self.search_loaded = False
        self.current_package_path = None
        self.current_search_package_cursor = None
        # test to reset portage
        #portage_lib.reload_portage()
        portage_lib.reload_world()
        # load the db
        self.dbtime = 0
        db.db.db_init(True)
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
        else:
            self.category_view.populate(db.db.categories.keys())
        self.package_view.clear()
        self.set_package_actions_sensitive(False, None)
        # update the views by calling view_filter_changed
        self.view_filter_changed(self.widget["view_filter"])
        #self.widget["view_refresh"].set_sensitive(False)
        return False

    def package_update(self, pkg):
        """callback function to update an individual package
            after a successfull emerge was detected"""
        # find the pkg in db.db
        db.db.update(portage_lib.extract_package(pkg))

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
        self.last_sync = get_sync_info()

    def set_sync_tip(self):
        """Sets the sync tip for the new or old toolbar API"""
        if self.new_toolbar_API:
            self.widget["btn_sync"].set_tooltip(self.synctooltip, ' '.join([self.sync_tip, self.last_sync[:-1], '']))
        else:
            self.synctooltip.set_tip(self.widget["btn_sync"], ' '.join([self.sync_tip, self.last_sync[:], '']))
        #self.synctooltip.enable()
        
        
    #~ def pkg_path_callback(self, path):
        #~ """callback function to save the path to the package that
        #~ matched the name passed to the populate() in PackageView"""
        #~ self.current_package_path = path
        #~ return

    def packageview_callback(self, action = None, arg = None):
        old_pretend_value = config.Prefs.emerge.pretend
        old_verbose_value = config.Prefs.emerge.verbose
        if action.startswith("emerge"):
            if "pretend" in action:
                config.Prefs.emerge.pretend = True
                config.Prefs.emerge.verbose = True
            else:
                config.Prefs.emerge.pretend = False
            if "sudo" in action:
                self.emerge_package(self.package_view, sudo=True)
            else:
                self.emerge_package(self.package_view)
        elif action.startswith("unmerge"):
            config.Prefs.emerge.pretend = False
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
            utils.debug.dprint("MAINWINDOW package_view callback: unknown action '%s'" % str(action))
        config.Prefs.emerge.pretend = old_pretend_value
        config.Prefs.emerge.verbose = old_verbose_value

    def summary_callback(self, action = None, arg = None):
        utils.debug.dprint("MAINWINDOW: summary_callback(): called")
        old_pretend_value = config.Prefs.emerge.pretend
        if action.startswith("emerge"):
            ebuild = arg
            cp = portage_lib.pkgsplit(ebuild)[0]
            if "pretend" in action:
                config.Prefs.emerge.pretend = True
            else:
                config.Prefs.emerge.pretend = False
            if "sudo" in action:
                self.setup_command( \
                    portage_lib.get_name(cp),
                    ''.join(['sudo -p "Password: " emerge',
                              config.Prefs.emerge.get_string(), '=', ebuild])
                )
            else:
                self.setup_command( \
                    portage_lib.get_name(cp),
                    ''.join(["emerge", config.Prefs.emerge.get_string(), '=', ebuild])
                )
        elif action.startswith("unmerge"):
            ebuild = arg
            cp = portage_lib.pkgsplit(ebuild)[0]
            config.Prefs.emerge.pretend = False
            if "sudo" in action:
                self.setup_command( \
                    portage_lib.get_name(cp),
                    ''.join(['sudo -p "Password: " emerge unmerge',
                    config.Prefs.emerge.get_string(), '=', ebuild])
                )
            else:
                self.setup_command(
                    portage_lib.get_name(cp),
                    ''.join(["emerge unmerge", config.Prefs.emerge.get_string(), '=', ebuild])
                )
        else:
            utils.debug.dprint("MAINWINDOW package_view callback: unknown action '%s'" % str(action))
        config.Prefs.emerge.pretend = old_pretend_value

    def check_for_root(self, *args):
        """figure out if the user can emerge or not..."""
        if not self.is_root:
            self.no_root_dialog = SingleButtonDialog(_("No root privileges"),
                            self.mainwindow,
                            _("In order to access all the features of Porthole,\n"
                            "please run it with root privileges."),
                            self.remove_nag_dialog,
                            _("_Ok"))

    def remove_nag_dialog(self, widget, response):
        """ Remove the nag dialog and set it to not display next time """
        self.no_root_dialog.destroy()
        config.Prefs.main.show_nag_dialog = False

    def set_statusbar2(self, to_string):
        """Update the statusbar without having to use push and pop."""
        #utils.debug.dprint("MAINWINDOW: set_statusbar2(); " + string)
        statusbar2 = self.wtree.get_widget("statusbar2")
        statusbar2.pop(0)
        statusbar2.push(0, to_string)

    def update_db_read(self, args): # extra args for dispatcher callback
        """Update the statusbar according to the number of packages read."""
        #utils.debug.dprint("MAINWINDOW: update_db_read()")
        #args ["nodecount", "allnodes_length","done"]
        if args["done"] == False:
            #self.dbtime += 1
            count = args["nodecount"]
            if count > 0:
                self.set_statusbar2(_("%(base)s: %(count)i packages read")
                                     % {'base':self.status_root, 'count':count})
            #utils.debug.dprint("config.Prefs.dbtime = ")
            #utils.debug.dprint(config.Prefs.dbtime)
            try:
                #fraction = min(1.0, max(0,(self.dbtime / float(config.Prefs.dbtime))))
                fraction = min(1.0, max(0, (count / float(args["allnodes_length"]))))
                self.progressbar.set_text(str(int(fraction * 100)) + "%")
                self.progressbar.set_fraction(fraction)
            except:
                pass

        elif args['db_thread_error']:
            # todo: display error dialog instead
            self.set_statusbar2(args['db_thread_error'].decode('ascii', 'replace'))
            return False  # disconnect from timeout
        else: # args["done"] == True - db_thread is done
            self.progressbar.set_text("100%")
            self.progressbar.set_fraction(1.0)
            self.set_statusbar2(_("%(base)s: Populating tree") % {'base':self.status_root})
            self.update_statusbar(SHOW_ALL)
            utils.debug.dprint("MAINWINDOW: setting menubar,toolbar,etc to sensitive...")
            for x in ["menubar","toolbar","view_filter","search_entry","btn_search","view_refresh"]:
                self.wtree.get_widget(x).set_sensitive(True)
            if self.plugin_manager and not self.plugin_manager.plugins: # no plugins
                self.wtree.get_widget("plugin_settings").set_sensitive(False)
            # make sure we search again if we reloaded!
            if self.widget["view_filter"].get_history() == SHOW_SEARCH:
                #utils.debug.dprint("MAINWINDOW: update_db_read()... Search view")
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
                #utils.debug.dprint("MAINWINDOW: update_db_read()... self.reload=True ALL or INSTALLED view")
                # reset _last_selected so it thinks this category is new again
                self.category_view._last_category = None
                #utils.debug.dprint("MAINWINDOW: re-select the category: self.current_category_cursor =")
                #utils.debug.dprint(self.current_category_cursor)
                #utils.debug.dprint(type(self.current_category_cursor))
                if (self.current_category_cursor != None) and (self.current_category_cursor != [None,None]):
                    # re-select the category
                    try:
                        self.category_view.set_cursor(self.current_category_cursor[0],
                                                      self.current_category_cursor[1])
                    except:
                        utils.debug.dprint("MAINWINDOW: update_db_read(); error converting self.current_category_cursor[]: %s"
                                %str(self.current_category_cursor))
                #~ #utils.debug.dprint("MAINWINDOW: reset _last_selected so it thinks this package is new again")
                # reset _last_selected so it thinks this package is new again
                self.package_view._last_selected = None
                #~ #utils.debug.dprint("MAINWINDOW: re-select the package")
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
                    #utils.debug.dprint("MAINWINDOW: update_db_read()... must be an upgradeable view")
                    self.widget['view_refresh'].set_sensitive(True)
                    ## hmm, don't mess with upgrade list after an emerge finishes.
                else:
                    utils.debug.dprint("MAINWINDOW: db_thread is done, reload_view()")
                    # need to wait until all other events are done for it to show when the window first opens
                    gobject.idle_add(self.reload_view)
            utils.debug.dprint("MAINWINDOW: Made it thru a reload, returning...")
            self.progress_done(False)
            #if not self.reload:
            #self.view_filter_changed(self.widget["view_filter"])
            self.reload = False
            return False  # disconnect from timeout
        #utils.debug.dprint("MAINWINDOW: returning from update_db_read() count=%d dbtime=%d"  %(count, self.dbtime))
        return True

    def db_save_variables(self):
        """recalulates and stores persistent database variables into the prefernces"""
        config.Prefs.database_size = db.db.db_thread.allnodes_length
        # store only the last 10 reload times
        if len(config.Prefs.dbtotals)==10:
            config.Prefs.dbtotals = config.Prefs.dbtotals[1:]+[str(self.dbtime)]
        else:
            config.Prefs.dbtotals += [str(self.dbtime)]
        # calculate the average time to use for the progress bar calculations
        total = 0
        count = 0
        for time in config.Prefs.dbtotals:
            total += int(time)
            count += 1
        #utils.debug.dprint("MAINWINDOW: db_save_variables(); total = %d : count = %d" %(total,count))
        config.Prefs.dbtime = int(total/count)
        utils.debug.dprint("MAINWINDOW: db_save_variables(); dbtime = %d" %self.dbtime)
        utils.debug.dprint("MAINWINDOW: db_save_variables(); new average load time = %d cycles" %config.Prefs.dbtime)


    def setup_command(self, package_name, command, run_anyway=False):
        """Setup the command to run or not"""
        if (self.is_root
                or run_anyway
                or (config.Prefs.emerge.pretend and not command.startswith(config.Prefs.globals.Sync))
                or command.startswith("sudo ")
                or utils.utils.pretend_check(command)):
            if command.startswith('sudo -p "Password: "'):
                utils.debug.dprint('MAINWINDOW: setup_command(); removing \'sudo -p "Password: "\' for pretend_check')
                is_pretend = utils.utils.pretend_check(command[21:])
            else:
                is_pretend = utils.utils.pretend_check(command)
            utils.debug.dprint("MAINWINDOW: setup_command(); emerge.pretend = %s, pretend_check = %s, help_check = %s, info_check = %s"\
                    %(str(config.Prefs.emerge.pretend), str(is_pretend), str(utils.utils.help_check(command)),\
                        str(utils.utils.info_check(command))))
            if (config.Prefs.emerge.pretend
                    or is_pretend
                    or utils.utils.help_check(command)
                    or utils.utils.info_check(command)):
                # temp set callback for testing
                #callback = self.sync_callback
                callback = lambda: None  # a function that does nothing
                utils.debug.dprint("MAINWINDOW: setup_command(); callback set to lambda: None")
            elif package_name == "Sync Portage Tree":
                callback = self.sync_callback #self.init_data
                utils.debug.dprint("MAINWINDOW: setup_command(); callback set to self.sync_callback")
            else:
                #utils.debug.dprint("MAINWINDOW: setup_command(); setting callback()")
                callback = self.reload_db
                utils.debug.dprint("MAINWINDOW: setup_command(); callback set to self.reload_db")
                #callback = self.package_update
            #ProcessWindow(command, env, config.Prefs, callback)
            self.process_manager.add(package_name, command, callback)
        else:
            utils.debug.dprint("MAINWINDOW: Must be root user to run command '%s' " % command)
            #self.sorry_dialog = utils.SingleButtonDialog(_("You are not root!"),
            #        self.mainwindow,
            #        _("Please run Porthole as root to emerge packages!"),
            #        None, "_Ok")
            self.check_for_root() # displays not root dialog
            return False
        return True
   
    def pretend_set(self, widget):
        """Set whether or not we are going to use the --pretend flag"""
        config.Prefs.emerge.pretend = widget.get_active()

    def fetch_set(self, widget):
        """Set whether or not we are going to use the --fetchonly flag"""
        config.Prefs.emerge.fetch = widget.get_active()

    def verbose_set(self, widget):
        """Set whether or not we are going to use the --verbose flag"""
        config.Prefs.emerge.verbose = widget.get_active()

    def upgradeonly_set(self, widget):
        """Set whether or not we are going to use the --upgradeonly flag"""
        config.Prefs.emerge.upgradeonly = widget.get_active()
        # reset the upgrades list due to the change
        self.upgrades_loaded = False
        if hasattr(self, "widget") and self.widget["view_filter"].get_history() == SHOW_UPGRADE:
            if self.ut_running: # aargh, kill it
                self.ut.please_die()
                utils.debug.dprint("MAINWINDOW: joining upgrade thread...")
                self.ut.join()
                utils.debug.dprint("MAINWINDOW: finished!")
                self.ut_running = False
            #utils.debug.dprint("MAINWINDOW: upgradeonly_set()...reload upgradeable view")
            self.package_view.clear()
            self.set_package_actions_sensitive(False, None)
            # update the views by calling view_filter_changed
            self.view_filter_changed(self.widget["view_filter"])
            self.reload_view(None)

    def search_set(self, widget):
        """Set whether or not to search descriptions"""
        config.Prefs.main.search_desc = widget.get_active()

    def emerge_package(self, widget, sudo=False):
        """Emerge the currently selected package."""
        package = utils.utils.get_treeview_selection(self.package_view, 2)
        if (sudo or (not utils.utils.is_root() and utils.utils.can_sudo())) \
                and not config.Prefs.emerge.pretend:
            self.setup_command(package.get_name(), 'sudo -p "Password: " emerge' +
                config.Prefs.emerge.get_string() + package.full_name)
        else:
            self.setup_command(package.get_name(), "emerge" +
                config.Prefs.emerge.get_string() + package.full_name)

    def adv_emerge_package(self, widget):
        """Advanced emerge of the currently selected package."""
        package = utils.utils.get_treeview_selection(self.package_view, 2)
        # Activate the advanced emerge dialog window
        # re_init_portage callback is for when package.use etc. are modified
        dialog = AdvancedEmergeDialog(package, self.setup_command, self.re_init_portage)

    def new_plugin_package_tab( self, name, callback, widget ):
        notebook = self.packagebook.notebook
        label = gtk.Label(name)
        notebook.append_page(widget, label)
        page_num = notebook.page_num(widget)
        self.plugin_package_tabs[name] = [callback, label, page_num]

    def del_plugin_package_tab( self, name ):
        notebook = self.packagebook.notebook
        notebook.remove_page(self.plugin_package_tabs[name][1])
        self.plugin_package_tabs.remove(name)

    def plugin_settings_activate( self, widget ):
        """Shows the plugin settings window"""
        plugin_dialog = PluginGUI(self.plugin_manager )
    
    def configure_porthole(self, menuitem_widget):
        """Shows the Configuration GUI"""
        config_dialog = ConfigDialog()
    
    def new_plugin_menuitem( self, label ):
        utils.debug.dprint("MAINWINDOW: Adding new Menu Entry")
        if self.needs_plugin_menu == False:
            #Creates plugin Menu
            utils.debug.dprint("MAINWINDOW: Enabling Plugin Menu")
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
        package = utils.utils.get_treeview_selection(self.package_view, 2)
        if (sudo or (not self.is_root and utils.utils.can_sudo())) \
                and not config.Prefs.emerge.pretend:
            self.setup_command(package.get_name(), 'sudo -p "Password: " emerge --unmerge' +
                    config.Prefs.emerge.get_string() + package.full_name)
        else:
            self.setup_command(package.get_name(), "emerge unmerge" +
                    config.Prefs.emerge.get_string() + package.full_name)

    def sync_tree(self, widget):
        """Sync the portage tree and reload it when done."""
        sync = config.Prefs.globals.Sync
        if config.Prefs.emerge.verbose:
            sync += " --verbose"
        if config.Prefs.emerge.nospinner:
            sync += " --nospinner "
        if utils.utils.is_root():
            self.setup_command("Sync Portage Tree", sync)
        elif utils.utils.can_sudo():
            self.setup_command("Sync Portage Tree", 'sudo -p "Password: " ' + sync)
        else:
            self.check_for_root()

    def on_cancel_btn(self, widget):
        """cancel button callback function"""
        utils.debug.dprint("MAINWINDOW: on_cancel_btn() callback")
        # terminate the thread
        self.ut.please_die()
        self.ut.join()
        self.progress_done(True)

    def on_window_state_event(self, widget, event):
        """Handler for window-state-event gtk callback.
        Just checks if the window is maximized or not"""
        if widget is not self.mainwindow: return False
        utils.debug.dprint("MAINWINDOW: on_window_state_event(); event detected")
        if gtk.gdk.WINDOW_STATE_MAXIMIZED & event.new_window_state:
            config.Prefs.main.maximized = True
        else:
            config.Prefs.main.maximized = False
    
    def on_pane_notify(self, pane, gparamspec):
        if gparamspec.name == "position":
            # bugfix for hpane jump bug. Now why does this happen?
            # it seems we need to reset the hpane the first time this gets called...
            #if self.hpane_bug:
                #self.hpane.set_position(config.Prefs.main.hpane)
                #self.hpane_bug = False
                #return True
            # save hpane, vpane positions
            config.Prefs.main.hpane = hpanepos = self.hpane.get_position()
            config.Prefs.main.vpane = vpanepos = self.vpane.get_position()
            utils.debug.dprint("MAINWINDOW on_pane_notify(): saved hpane %(hpanepos)s, vpane %(vpanepos)s" % locals())
    
    def upgrade_packages(self, widget):
        """Upgrade selected packages that have newer versions available."""
        if self.upgrades_loaded:
            utils.debug.dprint("MAINWINDOW: upgrade_packages() upgrades loaded")
            # create a list of packages to be upgraded
            self.packages_list = {}
            self.keyorder = []
            self.up_model = self.package_view.upgrade_model
            # read the upgrade tree into a list of packages to upgrade
            self.up_model.foreach(self.tree_node_to_list)
            if self.is_root or config.Prefs.emerge.pretend:
                emerge_cmd = "emerge --noreplace"
            elif utils.utils.can_sudo():
                emerge_cmd = 'sudo -p "Password: " emerge --noreplace'
            else: # can't sudo, not root
                # display not root dialog and return.
                self.check_for_root()
                return
            #utils.debug.dprint(self.packages_list)
            #utils.debug.dprint(self.keyorder)
            for key in self.keyorder:
                if not self.packages_list[key]:
                        utils.debug.dprint("MAINWINDOW: upgrade_packages(); dependancy selected: " + key)
                        if not self.setup_command(key, emerge_cmd +" --oneshot" +
                                config.Prefs.emerge.get_string() + key[:]): #use the full name
                            return
                elif not self.setup_command(key, emerge_cmd +
                                config.Prefs.emerge.get_string() + ' ' + key[:]): #use the full name
                    return
        else:
            utils.debug.dprint("MAIN: Upgrades not loaded; upgrade world?")
            self.upgrades_loaded_dialog = YesNoDialog(_("Upgrade requested"),
                    self.mainwindow,
                    _("Do you want to upgrade all packages in your world file?"),
                     self.upgrades_loaded_dialog_response)

    def tree_node_to_list(self, model, path, iter):
        """callback function from gtk.TreeModel.foreach(),
           used to add packages to an upgrades list"""
        if model.get_value(iter, 1):
            name = model.get_value(iter, 0)
            utils.debug.dprint("MAINWINDOW; tree_node_to_list(): name '%s'" % name)
            if name not in self.keyorder and name <> _("Upgradable dependencies:"):
                self.packages_list[name] = model.get_value(iter, 4) # model.get_value(iter, 2), name]
                self.keyorder = [name] + self.keyorder 
        return False


    def upgrades_loaded_dialog_response(self, widget, response):
        """ Get and parse user's response """
        if response == 0: # Yes was selected; upgrade all
            #self.load_upgrades_list()
            #self.upgrades_loaded_callback = self.upgrade_packages
            if not utils.utils.is_root() and utils.utils.can_sudo() \
                    and not config.Prefs.emerge.pretend:
                self.setup_command('world', 'sudo -p "Password: " emerge --update' +
                        config.Prefs.emerge.get_string() + 'world')
            else:
                self.setup_command('world', "emerge --update" +
                        config.Prefs.emerge.get_string() + 'world')
        else:
            # load the upgrades view to select which packages
            self.widget["view_filter"].set_history(SHOW_UPGRADE)
        # get rid of the dialog
        self.upgrades_loaded_dialog.destroy()

    def load_descriptions_list(self):
        """ Load a list of all descriptions for searching """
        self.desc_dialog = SingleButtonDialog(_("Please Wait!"),
                self.mainwindow,
                _("Loading package descriptions..."),
                self.desc_dialog_response, "_Cancel", True)
        utils.debug.dprint("MAINWINDOW: load_descriptions_list(); starting self.desc_thread")
        db.db.load_descriptions()
        db.db.set_desc_callback(self.desc_thread_update)

    def desc_dialog_response(self, widget, response):
        """ Get response from description loading dialog """
        # kill the update thread
        db.db.cancell_desc_update()
        self.desc_dialog.destroy()

    def desc_thread_update(self, args):
        """ Update status of description loading process """
        if args['done']:
            if not args['cancelled']:
                # search with descriptions
                self.package_search(None)
            self.desc_dialog.destroy()
            return False
        else:
            # print self.desc_thread.count
            if args['count']:
                fraction = args['count'] / float(len(db.db.list))
                self.desc_dialog.progbar.set_text(str(int(fraction * 100)) + "%")
                self.desc_dialog.progbar.set_fraction(fraction)
        return True

    def package_search(self, widget=None):
        """Search package db with a string and display results."""
        self.clear_package_detail()
        if not db.db.desc_loaded and config.Prefs.main.search_desc:
            self.load_descriptions_list()
            return
        tmp_search_term = self.wtree.get_widget("search_entry").get_text()
        #utils.debug.dprint(tmp_search_term)
        if tmp_search_term:
            # change view and statusbar so user knows it's searching.
            # This won't actually do anything unless we thread the search.
            self.search_loaded = True # or else v_f_c() tries to call package_search again
            self.widget["view_filter"].set_history(SHOW_SEARCH)
            if config.Prefs.main.search_desc:
                self.set_statusbar2(_("Searching descriptions for %s") % tmp_search_term)
            else:
                self.set_statusbar2(_("Searching for %s") % tmp_search_term)
            # call the thread
            self.search_thread = SearchReader(db.db.list, config.Prefs.main.search_desc, tmp_search_term, db.db.descriptions, Dispatcher(self.search_done))
            self.search_thread.start()
        return
            

    # start of search callback
    def search_done( self ):
            """show the search results from the search thread"""
            #if self.search_thread.done:
            if not self.search_thread.cancelled:
                # grab the list
                package_list = self.search_thread.package_list
                count = self.search_thread.pkg_count
                search_term = self.search_thread.search_term
                # kill off the thread
                self.search_thread.join()
            # in case the search view was already active
            self.update_statusbar(SHOW_SEARCH)
            self.search_history[search_term] = package_list
            self.search_history_counts[search_term] = count
            #Add the current search item & select it
            self.category_view.populate(self.search_history.keys(), True, self.search_history_counts)
            iter = self.category_view.model.get_iter_first()
            while iter != None:
                if self.category_view.model.get_value(iter, 1) == search_term:
                    selection = self.category_view.get_selection()
                    selection.select_iter(iter)
                    break
                iter = self.category_view.model.iter_next(iter)
            self.package_view.populate(package_list)
            if count == 1: # then select it
                self.current_search_package_name = package_list.keys()[0]
            self.category_view.last_category = search_term
            self.category_changed(search_term)

    def help_contents(self, widget):
        """Show the help file contents."""
        load_web_page('file://' + config.Prefs.DATA_PATH + 'help/index.html')

    def about(self, widget):
        """Show about dialog."""
        dialog = AboutDialog()

    def refresh(self):
        """Refresh PackageView"""
        utils.debug.dprint("MAINWINDOW: refresh()")
        mode = self.widget["view_filter"].get_history()
        if mode == SHOW_SEARCH:
            self.category_changed(self.current_search)
        else:
            self.category_changed(self.current_category)

    def category_changed(self, category):
        """Catch when the user changes categories."""
        mode = self.widget["view_filter"].get_history()
        # log the new category for reloads
        if mode not in [SHOW_SEARCH, SHOW_UPGRADE]:
            self.current_category = category
            self.current_category_cursor = self.category_view.get_cursor()
        #~ elif mode == SHOW_UPGRADE:
            #~ self.current_upgrade_category = category
            #~ self.current_upgrade_cursor = self.category_view.get_cursor()
        else:
            self.current_search = category
            self.current_search_cursor = self.category_view.get_cursor()
        if not self.reload:
            self.current_package_cursor = None
        #utils.debug.dprint("Category cursor = " +str(self.current_category_cursor))
        #utils.debug.dprint("Category = " + category)
        #utils.debug.dprint(self.current_category_cursor[0])#[1])
        if self.current_category_cursor:
            cursor = self.current_category_cursor[0]
            if cursor and len(cursor) > 1:
                sub_row = cursor[1] == None
            else:
                sub_row = False
        else:
            cursor = None
            sub_row = False
        self.clear_package_detail()
        if mode == SHOW_SEARCH:
            packages = self.search_history[category]
            #if len(packages) == 1: # then select it
            #    self.current_search_package_name = packages.values()[0].get_name()
            #self.package_view.populate(packages, self.current_search_package_name)
            # if search was a package name, select that one
            # (searching for 'python' for example would benefit)
            self.package_view.populate(packages, category)
        elif mode == SHOW_UPGRADE:
            packages = self.upgrades[category]
            self.package_view.populate(packages, self.current_package_name)
        elif not category or sub_row: #(self.current_category_cursor[0][1] == None):
            utils.debug.dprint("MAINWINDOW: category_changed(); category=False or self.current_category_cursor[0][1]==None")
            packages = None
            self.current_package_name = None
            self.current_package_cursor = None
            self.current_package_path = None
            self.package_view.PACKAGES = 0
            self.package_view.set_view(self.package_view.PACKAGES)
            self.package_view.clear()
        elif mode == SHOW_ALL:
            packages = db.db.categories[category]
            self.package_view.populate(packages, self.current_package_name)
        elif mode == SHOW_INSTALLED:
            packages = db.db.installed[category]
            self.package_view.populate(packages, self.current_package_name)
        else:
            raise Exception("The programmer is stupid. Unknown category_changed() mode");

    def clear_package_detail(self):
        self.packagebook.clear_notebook()
        self.set_package_actions_sensitive(False)


    def package_changed(self, package):
        """Catch when the user changes packages."""
        utils.debug.dprint("MAINWINDOW: package_changed()")
        if not package or package.full_name == "None":
            self.clear_package_detail()
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
        #utils.debug.dprint("Package name= %s, cursor = " %str(self.current_package_name))
        #utils.debug.dprint(self.current_package_cursor)
        # the notebook must be sensitive before anything is displayed
        # in the tabs, especially the deps_view
        self.set_package_actions_sensitive(True, package)
        self.packagebook.set_package(package)

    def view_filter_changed(self, widget):
        """Update the treeviews for the selected filter"""
        utils.debug.dprint("MAINWINDOW: view_filter_changed()")
        index = widget.get_history()
        utils.debug.dprint("MAINWINDOW: view_filter_changed(); index = %d" %index)
        self.update_statusbar(index)
        cat_scroll = self.wtree.get_widget("category_scrolled_window")
        self.category_view.set_search(False)
        self.clear_package_detail()
        if index in (SHOW_INSTALLED, SHOW_ALL):
            if index == SHOW_ALL:
                items = db.db.categories.keys()
                count = db.db.pkg_count
            else:
                items = db.db.installed.keys()
                count = db.db.installed_pkg_count
            self.category_view.populate(items, True, count)
            cat_scroll.show()
            utils.debug.dprint("MAINWINDOW: view_filter_changed(); reset package_view")
            self.package_view.set_view(self.package_view.PACKAGES)
            utils.debug.dprint("MAINWINDOW: view_filter_changed(); init package_view")
            self.package_view._init_view()
            #utils.debug.dprint("MAINWINDOW: view_filter_changed(); clear package_view")
            #self.package_view.clear()
            cat = self.current_category
            pack = self.current_package_name
            utils.debug.dprint("MAINWINDOW: view_filter_changed(); reselect category & package")
            #self.select_category_package(cat, pack, index)
        elif index == SHOW_SEARCH:
            self.category_view.set_search(True)
            if not self.search_loaded:
                self.set_package_actions_sensitive(False, None)
                self.category_view.populate(self.search_history.keys(), True, self.search_history_counts)
                self.package_search(None)
                self.search_loaded = True
            else:
                self.category_view.populate(self.search_history.keys(), True, self.search_history_counts)
            cat_scroll.show();
            utils.debug.dprint("MAIN: Showing search results")
            self.package_view.set_view(self.package_view.SEARCH_RESULTS)
            cat = self.current_search
            pack = self.current_search_package_name
            #self.select_category_package(cat, pack, index)
        elif index == SHOW_UPGRADE:
            utils.debug.dprint("MAINWINDOW: view_filter_changed(); upgrade selected")
            cat_scroll.show();
            self.package_view.set_view(self.package_view.UPGRADABLE)
            if not self.upgrades_loaded:
                utils.debug.dprint("MAINWINDOW: view_filter_changed(); calling load_upgrades_list ********************************")
                self.load_upgrades_list()
                self.package_view.clear()
                self.category_view.clear()
                utils.debug.dprint("MAINWINDOW: view_filter_changed(); back from load_upgrades_list()")
            else:
                self.category_view.populate(self.upgrades.keys(), False, self.upgrade_counts)
            self.package_view.set_view(self.package_view.UPGRADABLE)
            utils.debug.dprint("MAINWINDOW: view_filter_changed(); init package_view")
            self.package_view._init_view()
            #utils.debug.dprint("MAINWINDOW: view_filter_changed(); clear package_view")
            #self.package_view.clear()
            cat = self.current_upgrade_category
            pack = self.current_upgrade_package_name
        elif index == SHOW_REBUILD:
            utils.debug.dprint("MAINWINDOW: view_filter_changed(); Rebuild selected")
            cat = None #self.current_category
            pack = None #self.current_package_name
            pass
        utils.debug.dprint("MAINWINDOW: view_filter_changed(); reselect category & package")
        if cat and pack:
            self.select_category_package(cat, pack, index)
        # clear the notebook tabs
        #self.clear_package_detail()
        #if self.last_view_setting != index:
        utils.debug.dprint("MAINWINDOW: view_filter_changed(); last_view_setting changed")
        self.last_view_setting = index
        #self.current_category = None
        #self.category_view.last_category = None
        #self.current_category_cursor = None
        #self.current_package_cursor = None
    
    def select_category_package(self, cat, pack, index):
        utils.debug.dprint("MAINWINDOW: select_category_package(): %s / %s" % (cat, pack))
        model = self.category_view.get_model()
        iter = model.get_iter_first()
        catpath = None
        if index in [SHOW_INSTALLED, SHOW_ALL] and cat and '-' in cat:
            # find path of category
            catmaj, catmin = cat.split("-")
            #utils.debug.dprint("catmaj, catmin = %s, %s" % (catmaj, catmin))
            while iter:
                #utils.debug.dprint("value at iter %s: %s" % (iter, model.get_value(iter, 0)))
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
        elif index in [SHOW_SEARCH, SHOW_UPGRADE, SHOW_REBUILD]:
            while iter:
                if cat == model.get_value(iter, 0):
                    catpath = model.get_path(iter)
                    break
                iter = model.iter_next(iter)
        #elif index == SHOW_UPGRADE:
        #    catpath = 'Sure, why not?'
        else: utils.debug.dprint("MAINWINDOW: select_category_package(): bad index or category?")
        if catpath:
            if index: # != SHOW_UPGRADE:
                self.category_view.expand_to_path(catpath)
                self.category_view.last_category = None # so it thinks it's changed
                self.category_view.set_cursor(catpath)
            # now reselect whatever package we had selected
            model = self.package_view.get_model()
            iter = model.get_iter_first()
            path = None
            while iter:
                #utils.debug.dprint("value at iter %s: %s" % (iter, model.get_value(iter, 0)))
                if model.get_value(iter, 0).split('/')[-1] == pack:
                    path = model.get_path(iter)
                    self.package_view._last_selected = None
                    self.package_view.set_cursor(path)
                    break
                iter = model.iter_next(iter)
            if not path:
                utils.debug.dprint("MAINWINDOW: select_category_package(): no package found")
                self.clear_package_detail()
        else:
            utils.debug.dprint("MAINWINDOW: select_category_package(): no category path found")
            self.clear_package_detail()

    def load_upgrades_list(self):
        self.ut_progress = 1
        # upgrades are not loaded, create dialog and load them
        self.set_statusbar2(_("Generating 'system' packages list..."))
        # create upgrade thread for loading the upgrades
        #self.ut = UpgradableReader(Dispatcher(self.Update_upgrades, self.package_view, db.db.installed.items(),
        #                           config.Prefs.emerge.upgradeonly ))
        if self.ut_running:
            utils.debug.dprint("MAINWINDOW: load_upgrades_list(); upgrades thread already running!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return
        utils.debug.dprint("MAINWINDOW: load_upgrades_list(); starting upgrades thread")
        self.ut = UpgradableListReader(db.db.installed.items(),
                                   config.Prefs.emerge.upgradeonly)
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
            self.upgrades = self.ut.upgradables
            self.upgrade_counts = self.ut.pkg_count
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
                    self.packagebook.summary.update_package_info(None)
                    #self.wtree.get_widget("category_scrolled_window").hide()
            return False
        elif self.ut.progress < 2:
            # Still building system package list
            pass
        else:
            # stsatubar hack, should probably be converted to use a Dispatcher callback
            if self.ut.progress >= 2 and self.ut_progress == 1:
                self.set_statusbar2(_("Searching for upgradable packages..."))
                self.ut_progress = 2
            if self.ut_running:
                try:
                    if self.build_deps:
                        count = 0
                        for key in self.ut.pkg_count:
                            count += self.ut.pkg_count[key]
                        fraction = count / float(self.ut.upgrade_total)
                        self.progressbar.set_text(str(int(fraction * 100)) + "%")
                        self.progressbar.set_fraction(fraction)
                    else:
                        fraction = self.ut.count / float(db.db.installed_count)
                        self.progressbar.set_text(str(int(fraction * 100)) + "%")
                        self.progressbar.set_fraction(fraction)
                        if fraction == 1:
                            self.build_deps = True
                            self.set_statusbar2(_("Building Package List"))
                except Exception, e:
                    utils.debug.dprint("MAINWINDOW: update_upgrade_thread(): Exception: %s" % e)
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
            if not db.db:
                utils.debug.dprint("MAINWINDOW: attempt to update status bar with no db assigned")
            else:
                text = (_("%(pack)d packages in %(cat)d categories")
                        % {'pack':len(db.db.list), 'cat':len(db.db.categories)})
        elif mode == SHOW_INSTALLED:
            if not db.db:
                utils.debug.dprint("MAINWINDOW: attempt to update status bar with no db assigned")
            else:
                text = (_("%(pack)d packages in %(cat)d categories") 
                        % {'pack':db.db.installed_count, 'cat':len(db.db.installed)})
        elif mode == SHOW_SEARCH:
            text = '' #(_("%d matches found") % self.package_view.search_model.size)

        elif mode == SHOW_UPGRADE:
            if not self.ut:
                utils.debug.dprint("MAINWINDOW: attempt to update status bar with no upgrade thread assigned")
            else:
                text = '' #(_("%(world)d world, %(deps)d dependencies")
                           # % {'world':self.ut.pkg_count["World"], 'deps':self.ut.pkg_count["Dependencies"]})

        self.set_statusbar2(self.status_root + text)

    def set_package_actions_sensitive(self, enabled, package = None):
        """Sets package action buttons/menu items to sensitive or not"""
        #utils.debug.dprint("MAINWINDOW: set_package_actions_sensitive(%d)" %enabled)
        self.widget["emerge_package1"].set_sensitive(enabled)
        self.widget["adv_emerge_package1"].set_sensitive(enabled)
        self.widget["unmerge_package1"].set_sensitive(enabled)
        self.widget["btn_emerge"].set_sensitive(enabled)
        self.widget["btn_adv_emerge"].set_sensitive(enabled)
        if not enabled or enabled and package.get_installed():
            #utils.debug.dprint("MAINWINDOW: set_package_actions_sensitive() setting unmerge to %d" %enabled)
            self.widget["btn_unmerge"].set_sensitive(enabled)
            self.widget["unmerge_package1"].set_sensitive(enabled)
        else:
            #utils.debug.dprint("MAINWINDOW: set_package_actions_sensitive() setting unmerge to %d" %(not enabled))
            self.widget["btn_unmerge"].set_sensitive(not enabled)
            
            self.widget["unmerge_package1"].set_sensitive(not enabled)
        self.packagebook.notebook.set_sensitive(enabled)

    def size_update(self, widget, event):
        #utils.debug.dprint("MAINWINDOW: size_update(); called.")
        """ Store the window and pane positions """
        config.Prefs.main.width = event.width
        config.Prefs.main.height = event.height
        pos = widget.get_position()
        # note: event has x and y attributes but they do not give the same values as get_position().
        config.Prefs.main.xpos = pos[0]
        config.Prefs.main.ypos = pos[1]

    def open_log(self, widget):
        """ Open a log of a previous emerge in a new terminal window """
        newterm = ProcessManager(utils.utils.environment(), True)
        newterm.do_open(widget)

    def custom_run(self, widget):
        """ Run a custom command in the terminal window """
        #utils.debug.dprint("MAINWINDOW: entering custom_run")
        #utils.debug.dprint(config.Prefs.run_dialog.history)
        get_command = RunDialog(self.setup_command, run_anyway=True)

    def re_init_portage(self, *widget):
        """re-initializes the imported portage modules in order to see changines in any config files
        e.g. /etc/make.conf USE flags changed"""
        portage_lib.reload_portage()
        portage_lib.reset_use_flags()
##        if  self.current_package_cursor != None and self.current_package_cursor[0]: # should fix a type error in set_cursor; from pycrash report
##            # reset _last_selected so it thinks this package is new again
##            self.package_view._last_selected = None
##            # re-select the package
##            self.package_view.set_cursor(self.current_package_cursor[0],
##            self.current_package_cursor[1])
        self.view_filter_changed(self.widget["view_filter"])

    def quit(self, widget):
        if not self.confirm_delete():
            self.goodbye(None)
        return

    def goodbye(self, widget):
        """Main window quit function"""
        utils.debug.dprint("MAINWINDOW: goodbye(); quiting now")
        try: # for >=pygtk-2.3.94
            utils.debug.dprint("MAINWINDOW: gtk.main_quit()")
            gtk.main_quit()
        except: # use the depricated function
            utils.debug.dprint("MAINWINDOW: gtk.mainquit()")
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
            utils.debug.dprint("TERMINAL: kill(); not killing")
            return True
        #self.process_manager.confirm = False
        if self.process_manager.kill_process(None, False):
            utils.debug.dprint("MAINWINDOW: process killed, destroying window")
            self.process_manager.allow_delete = True
            self.process_manager.window.hide()
        return False

