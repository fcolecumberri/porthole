#!/usr/bin/env python

'''
    Porthole Main Window
    The main interface the user will interact with

    Copyright (C) 2003 - 2008
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
import datetime
id = datetime.datetime.now().microsecond
print "MAINWINDOW: id initialized to ", id

import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, gtk.glade, gobject
import os
from gettext import gettext as _

from porthole.utils import utils, debug
from porthole import config
from porthole import backends
portage_lib = backends.portage_lib
#World = portage_lib.settings.get_world
from porthole.utils.dispatcher import Dispatcher
from porthole.dialogs.about import AboutDialog
from porthole.dialogs.command import RunDialog
from porthole.dialogs.simple import SingleButtonDialog, YesNoDialog
from porthole.dialogs.configure import ConfigDialog
from porthole.packagebook.notebook import PackageNotebook
from porthole.packagebook.depends import DependsTree
from porthole.terminal.terminal import ProcessManager
from porthole.views.category import CategoryView
from porthole.views.package import PackageView, PACKAGES, SEARCH, UPGRADABLE, DEPRECATED, SETS, BLANK, TEMP
from porthole.views.models import MODEL_ITEM as PACKAGE_MODEL_ITEM
#from porthole.views.depends import DependsView
from porthole.views.commontreeview import CommonTreeView
from porthole.advancedemerge.advemerge import AdvancedEmergeDialog
from porthole.plugin import PluginGUI, PluginManager
from porthole.readers.upgradeables import UpgradableListReader
from porthole.readers.descriptions import DescriptionReader
from porthole.readers.deprecated import DeprecatedReader
from porthole.readers.search import SearchReader
from porthole.readers.sets import SetListReader
from porthole.loaders.loaders import *
from porthole.backends.version_sort import ver_match
from porthole.backends.utilities import get_sync_info
from porthole import db
#from timeit import Timer


SHOW_ALL = 0
SHOW_INSTALLED = 1
SHOW_SEARCH = 2
SHOW_UPGRADE = 3
SHOW_DEPRECATED = 4
SHOW_SETS = 5
INDEX_TYPES = ["All", "Installed", "Search", "Upgradable", "Deprecated", "Sets"]
GROUP_SELECTABLE = [SHOW_UPGRADE, SHOW_DEPRECATED , SHOW_SETS]
ON = True
OFF = False
# create the translated reader type names
READER_NAMES = {"Deprecated": _("Deprecated"), "Sets": _("Sets"), "Upgradable": _("Upgradable")}

def check_glade():
        """determine the libglade version installed
        and return the correct glade file to use"""
        porthole_gladefile = "glade/porthole.glade"
        #return porthole_gladefile
        # determine glade version
        versions = portage_lib.get_installed("gnome-base/libglade")
        if versions:
            debug.dprint("libglade: %s" % versions)
            old, new = ver_match(versions, ["2.0.1","2.4.9-r99"], ["2.5.0","2.99.99"])
            if old:
                debug.dprint("MAINWINDOW: Check_glade(); Porthole no longer supports the older versions\n"+\
                        "of libglade.  Please upgrade libglade to >=2.5.0 for all GUI features to work")
                porthole_gladefile = "glade/porthole.glade"
                new_toolbar_API = False
            elif new:
                porthole_gladefile = "glade/porthole.glade"  # formerly "porthole-new2.glade"
                new_toolbar_API = True
        else:
            debug.dprint("MAINWINDOW: No version list returned for libglade")
            return None, None
        debug.dprint("MAINWINDOW: __init__(); glade file = %s" %porthole_gladefile)
        return porthole_gladefile, new_toolbar_API

class MainWindow:
    """Main Window class to setup and manage main window interface."""
    def __init__(self) :#, preferences = None, configs = None):
        debug.dprint("MAINWINDOW: process id = %d ****************" %os.getpid())
        config.Prefs.use_gladefile, self.new_toolbar_API = check_glade()
        # setup prefs
        config.Prefs.myarch = portage_lib.get_arch()
        debug.dprint("MAINWINDOW: Prefs.myarch = " + config.Prefs.myarch)
        #self.config = configs
        # setup glade
        self.gladefile = config.Prefs.DATA_PATH + config.Prefs.use_gladefile
        self.wtree = gtk.glade.XML(self.gladefile, "main_window", config.Prefs.APP)
        option = 'empty'
        # register callbacks  note: gtk.mainquit deprecated
        callbacks = {
            "on_main_window_destroy" : self.goodbye,
            "on_quit1_activate" : self.quit,
            "on_emerge_package" : self.emerge_btn,
            "on_adv_emerge_package" : self.adv_emerge_btn,
            "on_unmerge_package" : self.unmerge_btn,
            "on_sync_tree" : self.sync_tree,
            "on_upgrade_packages" : self.upgrade_packages,
            "on_package_search" : self.package_search,
            "on_search_entry_activate": self.package_search,
            "on_help_contents" : self.help_contents,
            "on_about" : self.about,
            "view_filter_changed" : self.view_filter_changed,
            "on_search_descriptions1_activate" : self.search_set,
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
        # save the mainwindow widget to Config for use by other modules as a parent window
        config.Mainwindow = self.mainwindow
        callbacks = {
            "action_callback" : self.action_callback,
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
        #self.package_view.register_callbacks(self.packageview_callback)
        self.package_view.register_callbacks(self.action_callback)
        result = self.wtree.get_widget("package_scrolled_window").add(self.package_view)
        # how should we setup our saved menus?
        settings = ["pretend", "fetch", "update", "verbose", "noreplace", "oneshot"] # "search_descriptions1"]
        for option in settings:
            widget = self.wtree.get_widget(option)
            state = getattr(config.Prefs.emerge, option) or False
            debug.dprint("MAINWINDOW: __init__(); option = %s, state = %s" %(option, str(state)))
            widget.set_active(state)
            widget.connect("activate", self.emerge_setting_set, option)
        # setup a convienience tuple
        self.tool_widgets = ["emerge_package1","adv_emerge_package1","unmerge_package1","btn_emerge",
                     "btn_adv_emerge","btn_unmerge", "btn_sync", "view_refresh", "view_filter"]
        self.widget = {}
        for x in self.tool_widgets:
            self.widget[x] = self.wtree.get_widget(x)
            if not self.widget[x]:
                debug.dprint("MAINWINDOW: __init__(); Failure to obtain widget '%s'" %x)
        # get an empty tooltip
        ##self.synctooltip = gtk.Tooltips()
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
        #debug.dprint("MAINWINDOW: __init__() before hpane; %d, vpane; %d" %(config.Prefs.main.hpane, config.Prefs.main.vpane))
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
        #self.hpane_bug = True
        # initialize now so that the update_db_callback doesn't puke
        self.plugin_manager = None
        self.plugin_package_tabs = {}
        # initialize our data
        self.init_data()
        # set if we are root or not
        self.is_root = utils.is_root()
        debug.dprint("MAINWINDOW: __init__(); is_root = " + str(self.is_root))
        if config.Prefs.main.show_nag_dialog:
            # let the user know if he can emerge or not
            self.check_for_root()
        self.toolbar_expander = self.wtree.get_widget("toolbar_expander")
        # This should be set in the glade file, but doesn't seem to work ?
        self.toolbar_expander.set_expand(True)
        # create and start our process manager
        self.process_manager = ProcessManager(utils.environment(), False)
        # populate the view_filter menu
        self.widget["view_filter_list"] = gtk.ListStore(str)
        for i in [_("All Packages"), _("Installed Packages"), _("Search Results"), _("Upgradable Packages"),
                    _("Deprecated Packages"), _("Sets")]:
            self.widget["view_filter_list"].append([i])
        self.widget["view_filter"].set_model(self.widget["view_filter_list"])
        self.widget["view_filter"].set_active(SHOW_ALL)
        self.setup_plugins()
        debug.dprint("MAINWINDOW: Showing main window")
        self.mainwindow.show_all()
        if self.is_root:
            # hide warning toolbar widget
            debug.dprint("MAINWINDOW: __init__(); hiding btn_root_warning")
            self.wtree.get_widget("btn_root_warning").hide()

    def setup_plugins(self):
        #Plugin-related statements
        self.needs_plugin_menu = False
        #debug.dprint("MAIN; setup_plugins(): path_list %s" % config.Prefs.plugins.path_list)
        debug.dprint("MAIN: setup_plugins: plugin path: %s" % config.Prefs.PLUGIN_DIR)
        self.plugin_root_menu = gtk.MenuItem(_("Active Plugins"))
        self.plugin_menu = gtk.Menu()
        self.plugin_root_menu.set_submenu(self.plugin_menu)
        self.wtree.get_widget("menubar").append(self.plugin_root_menu)
        self.plugin_manager = PluginManager(self)
        self.plugin_package_tabs = {}

    def init_data(self):
        # set things we can't do unless a package is selected to not sensitive
        self.set_package_actions_sensitive(False)
        debug.dprint("MAINWINDOW: init_data(); Initializing data")
        # set status
        #self.set_statusbar(_("Obtaining package list "))
        self.status_root = _("Loading database")
        self.set_statusbar2(_("Initializing database. Please wait..."))
        self.progressbar = self.wtree.get_widget("progressbar1")
        self.set_cancel_btn(OFF)
        db.db.set_callback(self.update_db_read)
        # init some dictionaries
        self.loaded_callback = {}
        self.current_cat_name = {}
        self.current_cat_cursor = {}
        self.current_pkg_name = {}
        self.current_pkg_cursor = {}
        self.current_pkg_path = {}
        self.pkg_list = {}
        self.pkg_count = {}
        self.loaded = {}
        for i in ["All", "Installed", "Upgradable", "Deprecated", "Search", "Sets"]:
            self.current_cat_name[i] = None
            self.current_cat_cursor[i] = None
            self.current_pkg_name[i] = None
            self.current_pkg_cursor[i] = None
            self.current_pkg_path[i] = None
            if i not  in ["All", "Installed"]:
                # init pkg lists, counts
                self.pkg_list[i] =  {}
                self.pkg_count[i] =  {}
                self.loaded[i] = False
            if i in ["Upgradable", "Deprecated", "Sets"]:
                self.loaded_callback[i] = None

        # next add any index names that need to be reset on a reload
        self.loaded_resets = ["Search", "Deprecated"]
        self.current_search = None
        # descriptions loaded?
        #self.desc_loaded = False
        # view filter setting
        self.last_view_setting = None
        # set notebook tabs to load new package info
        self.packagebook.reset_tabs()
        self.reader_running = False
        self.reader = None
        # load the db
        #debug.dprint("MAINWINDOW: init_db(); starting db.db.db_thread")
        self.reload = False
        self.upgrade_view = False
        #self.db_timeout = gobject.timeout_add(100, self.update_db_read)
        self.last_sync = _("Unknown")
        self.valid_sync = False
        self.get_sync_time()
        self.set_sync_tip()
        self.new_sync = False
        self.reload_depth = 0

    def reload_db(self, *widget):
        debug.dprint("MAINWINDOW: reload_db() callback")
        self.progress_done(True)
        for x in self.loaded_resets:
            self.loaded[x] = False
        for i in ["All", "Installed"]:
            self.current_pkg_path[i] = None
        self.current_pkg_cursor["Search"] = None
        # test to reset portage
        #portage_lib.reload_portage()
        portage_lib.settings.reload_world()
        self.upgrade_view = False
        self.get_sync_time()
        self.set_sync_tip()
        # load the db
        #self.dbtime = 0
        db.db.db_init(self.new_sync)
        #test = 87/0  # used to test pycrash is functioning
        self.reload = True
        self.new_sync = False
        # set status
        #self.set_statusbar(_("Obtaining package list "))
        self.status_root = _("Reloading database")
        self.set_statusbar2(self.status_root)
        return False

    def reload_view(self, *widget):
        """reload the package view"""
        if self.widget["view_filter"].get_active() == SHOW_UPGRADE:
            self.loaded["Upgradable"] = False
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
        #self.re_init_portage()
        portage_lib.settings.reset()
        # self.reload==False is currently broken for init_data when reloading after a sync
        #self.init_data() 
        self.new_sync = True
        self.reload_db()
        self.refresh()

    def get_sync_time(self):
        """gets and returns the timestamp info saved during
           the last portage tree sync"""
        self.last_sync, self.valid_sync = get_sync_info()

    def set_sync_tip(self):
        """Sets the sync tip for the new or old toolbar API"""
        ##if self.new_toolbar_API:
        self.widget["btn_sync"].set_has_tooltip(True) #self.synctooltip)
        self.widget["btn_sync"].set_tooltip_text(' '.join([self.sync_tip, self.last_sync[:], '']))
        ##else:
        ##    self.synctooltip.set_text(' '.join([self.sync_tip, self.last_sync[:], '']))
        ##self.synctooltip.enable()
        
    def action_callback(self, action = None, arg = None):
        debug.dprint("MAINWINDOW: action_callback(); caller = %s, action = '%s', arg = %s" %(arg['caller'], str(action), str(arg)))
        old_pretend_value = config.Prefs.emerge.pretend
        old_verbose_value = config.Prefs.emerge.verbose
        if "adv_emerge" in action:
            if 'package' in arg:
                package = arg['package']
            elif 'full_name' in arg:
                package = db.db.get_package(arg['full_name'])
            else:
                debug.dprint("MAINWINDOW: action_callback(); did not get an expected arg variable for 'adv_emerge' action arg = " + str(arg))
                return false
            self.adv_emerge_package( package)
            return True
        elif "set path" in action:
            # save the path to the package that matched the name passed
            # to populate() in PackageView... (?)
            x = self.widget["view_filter"].get_active()
            self.current_pkg_path[x] = arg['path'] # arg = path
        elif "package changed" in action:
            self.package_changed(arg['package'])
            return True
        elif "refresh" in action:
            self.refresh()
            return True
        elif "emerge" in action:
            commands = ["emerge "]
        elif  "unmerge" in action:
            commands = ["emerge --unmerge "]
        if "pretend" in action:
            config.Prefs.emerge.pretend = True
        else:
            config.Prefs.emerge.pretend = False
        if "sudo" in action:
            commands = ['sudo -p "Password: " '] + commands
        commands.append(config.Prefs.emerge.get_string())
        if "ebuild" in arg:
            commands.append('=' + arg['ebuild'])
            cp = portage_lib.pkgsplit(arg['ebuild'])[0]
        elif 'package' in arg:
            cp = arg['package'].full_name
            commands.append(arg['package'].full_name)
        elif 'full_name' in arg:
            cp = arg['full_name']
            commands.append(arg['full_name'])
        else:
            debug.dprint("MAINWINDOW action_callback(): unknown arg '%s'" % str(arg))
            return False
        self.setup_command(portage_lib.get_name(cp), ''.join(commands))
        config.Prefs.emerge.pretend = old_pretend_value
        config.Prefs.emerge.verbose = old_verbose_value
        return True

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
        #debug.dprint("MAINWINDOW: set_statusbar2(); " + string)
        statusbar2 = self.wtree.get_widget("statusbar2")
        statusbar2.pop(0)
        statusbar2.push(0, to_string)

    def update_db_read(self, args): # extra args for dispatcher callback
        """Update the statusbar according to the number of packages read."""
        #debug.dprint("MAINWINDOW: update_db_read()")
        #args ["nodecount", "allnodes_length","done"]
        if args["done"] == False:
            #self.dbtime += 1
            count = args["nodecount"]
            if count > 0:
                self.set_statusbar2(_("%(base)s: %(count)i packages read")
                                     % {'base':self.status_root, 'count':count})
            #debug.dprint("config.Prefs.dbtime = ")
            #debug.dprint(config.Prefs.dbtime)
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
            debug.dprint("MAINWINDOW: setting menubar,toolbar,etc to sensitive...")
            for x in ["menubar","toolbar","view_filter","search_entry","btn_search","view_refresh"]:
                self.wtree.get_widget(x).set_sensitive(True)
            if self.plugin_manager and not self.plugin_manager.plugins: # no plugins
                self.wtree.get_widget("plugin_settings").set_sensitive(False)
            # make sure we search again if we reloaded!
            mode = self.widget["view_filter"].get_active()
            debug.dprint("MAINWINDOW: update_db_read() mode = " + str(mode) + ' type = ' + str(type(mode)))
            if  mode in [SHOW_SEARCH]:
                #debug.dprint("MAINWINDOW: update_db_read()... Search view")
                # update the views by calling view_filter_changed
                self.view_filter_changed(self.widget["view_filter"])
                # reset the upgrades list if it is loaded and not being viewed
                self.loaded["Upgradable"] = False
                if self.reload:
                    # reset _last_selected so it thinks this package is new again
                    self.package_view._last_selected = None
                    if self.current_pkg_cursor["Search"] != None \
                            and self.current_pkg_cursor["Search"][0]: # should fix a type error in set_cursor; from pycrash report
                        # re-select the package
                        self.package_view.set_cursor(self.current_pkg_cursor["Search"][0],
                                                     self.current_pkg_cursor["Search"][1])
            elif self.reload and mode in [SHOW_ALL, SHOW_INSTALLED]:
                #debug.dprint("MAINWINDOW: update_db_read()... self.reload=True ALL or INSTALLED view")
                # reset _last_selected so it thinks this category is new again
                self.category_view._last_category = None
                #debug.dprint("MAINWINDOW: re-select the category: self.current_cat_cursor["All_Installed"] =")
                #debug.dprint(self.current_cat_cursor["All_Installed"])
                #debug.dprint(type(self.current_cat_cursor["All_Installed"]))
                if (self.current_cat_cursor[INDEX_TYPES[mode]] != None) and (self.current_cat_cursor[INDEX_TYPES[mode]] != [None,None]):
               # re-select the category
                    try:
                        self.category_view.set_cursor(self.current_cat_cursor[INDEX_TYPES[mode]][0], self.current_cat_cursor[INDEX_TYPES[mode]][1])
                    except:
                        debug.dprint('MAINWINDOW: update_db_read(); error converting self.current_cat_cursor[' + str(mode) + '][]: %s'
                                %str(self.current_cat_cursor[INDEX_TYPES[mode]]))
                #~ #debug.dprint("MAINWINDOW: reset _last_selected so it thinks this package is new again")
                # reset _last_selected so it thinks this package is new again
                self.package_view._last_selected = None
                #~ #debug.dprint("MAINWINDOW: re-select the package")
                # re-select the package
                if self.current_pkg_path[INDEX_TYPES[mode]] != None:
                    if self.current_pkg_cursor[INDEX_TYPES[mode]] != None and self.current_pkg_cursor[INDEX_TYPES[mode]][0]:
                        self.package_view.set_cursor(self.current_pkg_path[INDEX_TYPES[mode]],
                                                     self.current_pkg_cursor[INDEX_TYPES[mode]][1])
                self.view_filter_changed(self.widget["view_filter"])
                # reset the upgrades list if it is loaded and not being viewed
                self.loaded["Upgradable"] = False
            else:
                if self.reload:
                    #debug.dprint("MAINWINDOW: update_db_read()... must be an Upgradable view")
                    self.widget['view_refresh'].set_sensitive(True)
                    ## hmm, don't mess with upgrade list after an emerge finishes.
                else:
                    debug.dprint("MAINWINDOW: db_thread is done, reload_view()")
                    # need to wait until all other events are done for it to show when the window first opens
                    gobject.idle_add(self.reload_view)
            debug.dprint("MAINWINDOW: Made it thru a reload, returning...")
            self.progress_done(False)
            #if not self.reload:
            #self.view_filter_changed(self.widget["view_filter"])
            self.reload = False
            return False  # disconnect from timeout
        #debug.dprint("MAINWINDOW: returning from update_db_read() count=%d dbtime=%d"  %(count, self.dbtime))
        return True

    def db_save_variables(self):
        """recalulates and stores persistent database variables into the prefernces"""
        debug.dprint("MAINWINDOW: db_save_variables(); DEPRECATED function!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        #~ config.Prefs.database_size = db.db.db_thread.allnodes_length
        #~ # store only the last 10 reload times
        #~ if len(config.Prefs.dbtotals)==10:
            #~ config.Prefs.dbtotals = config.Prefs.dbtotals[1:]+[str(self.dbtime)]
        #~ else:
            #~ config.Prefs.dbtotals += [str(self.dbtime)]
        #~ # calculate the average time to use for the progress bar calculations
        #~ total = 0
        #~ count = 0
        #~ for time in config.Prefs.dbtotals:
            #~ total += int(time)
            #~ count += 1
        #~ #debug.dprint("MAINWINDOW: db_save_variables(); total = %d : count = %d" %(total,count))
        #~ config.Prefs.dbtime = int(total/count)
        #~ debug.dprint("MAINWINDOW: db_save_variables(); dbtime = %d" %self.dbtime)
        #~ debug.dprint("MAINWINDOW: db_save_variables(); new average load time = %d cycles" %config.Prefs.dbtime)


    def setup_command(self, package_name, command, run_anyway=False):
        """Setup the command to run or not"""
        if (self.is_root
                or run_anyway
                or (config.Prefs.emerge.pretend and not command.startswith(config.Prefs.globals.Sync))
                or command.startswith("sudo ")
                or utils.pretend_check(command)):
            if command.startswith('sudo -p "Password: "'):
                debug.dprint('MAINWINDOW: setup_command(); removing \'sudo -p "Password: "\' for pretend_check')
                is_pretend = utils.pretend_check(command[21:])
            else:
                is_pretend = utils.pretend_check(command)
            debug.dprint("MAINWINDOW: setup_command(); emerge.pretend = %s, pretend_check = %s, help_check = %s, info_check = %s"\
                    %(str(config.Prefs.emerge.pretend), str(is_pretend), str(utils.help_check(command)),\
                        str(utils.info_check(command))))
            if (config.Prefs.emerge.pretend
                    or is_pretend
                    or utils.help_check(command)
                    or utils.info_check(command)):
                # temp set callback for testing
                #callback = self.sync_callback
                callback = lambda: None  # a function that does nothing
                debug.dprint("MAINWINDOW: setup_command(); callback set to lambda: None")
            elif package_name == "Sync Portage Tree":
                callback = self.sync_callback #self.init_data
                debug.dprint("MAINWINDOW: setup_command(); callback set to self.sync_callback")
            else:
                #debug.dprint("MAINWINDOW: setup_command(); setting callback()")
                callback = self.reload_db
                debug.dprint("MAINWINDOW: setup_command(); callback set to self.reload_db")
                #callback = self.package_update
            #ProcessWindow(command, env, config.Prefs, callback)
            self.process_manager.add(package_name, command, callback, _("Porthole Main Window"))
        else:
            debug.dprint("MAINWINDOW: Must be root user to run command '%s' " % command)
            #self.sorry_dialog = utils.SingleButtonDialog(_("You are not root!"),
            #        self.mainwindow,
            #        _("Please run Porthole as root to emerge packages!"),
            #        None, "_Ok")
            self.check_for_root() # displays not root dialog
            return False
        return True
   
    def emerge_setting_set(self, widget, option='null'):
        """Set whether or not we are going to use an emerge option"""
        debug.dprint("MAINWINDOW: emerge_setting_set(%s)" %option)
        debug.dprint("MAINWINDOW: emerge_setting_set; " + str(widget) + " " + option)
        setattr(config.Prefs.emerge, option, widget.get_active())
        #config.Prefs.emerge.oneshot = widget.get_active()


    def search_set(self, widget):
        """Set whether or not to search descriptions"""
        config.Prefs.main.search_desc = widget.get_active()

    def emerge_btn(self, widget, sudo=False):
        """callback for the emerge toolbutton and menu entries"""
        package = utils.get_treeview_selection(self.package_view, 2)
        self.emerge_package(package, sudo)

    def emerge_package(self, package, sudo=False):
        """Emerge the package."""
        if (sudo or (not utils.is_root() and utils.can_sudo())) \
                and not config.Prefs.emerge.pretend:
            self.setup_command(package.get_name(), 'sudo -p "Password: " emerge' +
                config.Prefs.emerge.get_string() + package.full_name)
        else:
            self.setup_command(package.get_name(), "emerge" +
                config.Prefs.emerge.get_string() + package.full_name)

    def adv_emerge_btn(self, widget):
        """Advanced emerge of the currently selected package."""
        package = utils.get_treeview_selection(self.package_view, 2)
        self.adv_emerge_package(package)

    def adv_emerge_package(self, package):
        """Advanced emerge of the package."""
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
        debug.dprint("MAINWINDOW: Adding new Menu Entry")
        if self.needs_plugin_menu == False:
            #Creates plugin Menu
            debug.dprint("MAINWINDOW: Enabling Plugin Menu")
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

    def unmerge_btn(self, widget, sudo=False):
        """callback for the Unmerge button and menu entry to
        unmerge the currently selected package."""
        package = utils.get_treeview_selection(self.package_view, 2)
        self.unmerge_package(package, sudo)

    def unmerge_package(self, package, sudo=False):
        """Unmerge the package."""
        if (sudo or (not self.is_root and utils.can_sudo())) \
                and not config.Prefs.emerge.pretend:
            self.setup_command(package.get_name(), 'sudo -p "Password: " emerge --unmerge' +
                    config.Prefs.emerge.get_string() + package.full_name)
        else:
            self.setup_command(package.get_name(), "emerge --unmerge" +
                    config.Prefs.emerge.get_string() + package.full_name)

    def sync_tree(self, *widget):
        """Sync the portage tree and reload it when done."""
        sync = config.Prefs.globals.Sync
        if config.Prefs.emerge.verbose:
            sync += " --verbose"
        if config.Prefs.emerge.nospinner:
            sync += " --nospinner "
        if utils.is_root():
            self.setup_command("Sync Portage Tree", sync)
        elif utils.can_sudo():
            self.setup_command("Sync Portage Tree", 'sudo -p "Password: " ' + sync)
        else:
            self.check_for_root()

    def on_cancel_btn(self, widget):
        """cancel button callback function"""
        debug.dprint("MAINWINDOW: on_cancel_btn() callback")
        # terminate the thread
        self.reader.please_die()
        self.reader.join()
        self.progress_done(True)

    def on_window_state_event(self, widget, event):
        """Handler for window-state-event gtk callback.
        Just checks if the window is maximized or not"""
        if widget is not self.mainwindow: return False
        debug.dprint("MAINWINDOW: on_window_state_event(); event detected")
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
            debug.dprint("MAINWINDOW on_pane_notify(): saved hpane %(hpanepos)s, vpane %(vpanepos)s" % locals())
    
    def get_selected_list(self):
        """creates self.packages_list, self.keyorder"""
        debug.dprint("MAINWINDOW: get_selected_list()")
        my_type = INDEX_TYPES[self.last_view_setting]
        if self.last_view_setting not in GROUP_SELECTABLE:
            debug.dprint("MAINWINDOW: get_selected_list() " + my_type + " view is not group selectable for emerge/upgrade commands")
            return False
        # create a list of packages to be upgraded
        self.packages_list = {}
        self.keyorder = []
        if self.loaded[my_type]:
            debug.dprint("MAINWINDOW: get_selected_list() '" + my_type + "' loaded")
            self.list_model = self.package_view.view_model[my_type]
            # read the my_type tree into a list of packages
            debug.dprint("MAINWINDOW: get_selected_list(); run list_model.foreach() len = " + str(len(self.list_model)))
            debug.dprint("MAINWINDOW: get_selected_list(); self.list_model = " +str(self.list_model))
            self.list_model.foreach(self.tree_node_to_list)
            debug.dprint("MAINWINDOW: get_selected_list(); list_model.foreach() Done")
            debug.dprint("MAINWINDOW: get_selected_list(); len(self.packages_list) = " + str(len(self.packages_list)))
            debug.dprint("MAINWINDOW: get_selected_list(); self.keyorder) = " + str(self.keyorder))
            return len(self.keyorder)>0
        else:
            debug.dprint("MAINWINDOW: get_selected_list() " + my_type + " not loaded")
            return False

    def upgrade_packages(self, widget):
        """Upgrade selected packages that have newer versions available."""
        if self.last_view_setting in GROUP_SELECTABLE:
            if not self.get_selected_list():
                debug.dprint("MAINWINDOW: upgrade_packages(); No packages were selected")
                return
            debug.dprint("MAINWINDOW: upgrade_packages(); packages were selected")
            if self.is_root or config.Prefs.emerge.pretend:
                emerge_cmd = "emerge "
            elif utils.can_sudo():
                emerge_cmd = 'sudo -p "Password: " emerge '
            else: # can't sudo, not root
                # display not root dialog and return.
                self.check_for_root()
                return
            #debug.dprint(self.packages_list)
            #debug.dprint(self.keyorder)
            for key in self.keyorder:
                if not self.packages_list[key].in_world:
                        debug.dprint("MAINWINDOW: upgrade_packages(); dependancy selected: " + key)
                        options = config.Prefs.emerge.get_string()
                        if "--oneshot" not in options:
                            options = options + " --oneshot "
                        if not self.setup_command(key, emerge_cmd  + options + key[:]): #use the full name
                            return
                elif not self.setup_command(key, emerge_cmd +
                                config.Prefs.emerge.get_string() + ' ' + key[:]): #use the full name
                    return
        else:
            debug.dprint("MAIN: Upgrades not loaded; upgrade world?")
            self.upgrades_loaded_dialog = YesNoDialog(_("Upgrade requested"),
                    self.mainwindow,
                    _("Do you want to upgrade all packages in your world file?"),
                     self.upgrades_loaded_dialog_response)

    def tree_node_to_list(self, model, path, iter):
        """callback function from gtk.TreeModel.foreach(),
           used to add packages to the self.packages_list, self.keyorder lists"""
        #debug.dprint("MAINWINDOW; tree_node_to_list(): begin building list")
        if model.get_value(iter, PACKAGE_MODEL_ITEM["checkbox"]):
            name = model.get_value(iter, PACKAGE_MODEL_ITEM["name"])
            #debug.dprint("MAINWINDOW; tree_node_to_list(): name '%s'" % name)
            if name not in self.keyorder and name <> _("Upgradable dependencies:"):
                self.packages_list[name] = model.get_value(iter, PACKAGE_MODEL_ITEM["package"])
                #model.get_value(iter, PACKAGE_MODEL_ITEM["world"])
                # model.get_value(iter, PACKAGE_MODEL_INDEX["package"]), name]
                self.keyorder = [name] + self.keyorder 
        #debug.dprint("MAINWINDOW; tree_node_to_list(): new keyorder list = " + str(self.keyorder))
        return False


    def upgrades_loaded_dialog_response(self, widget, response):
        """ Get and parse user's response """
        if response == 0: # Yes was selected; upgrade all
            #self.load_upgrades_list()
            #self.loaded_callback["Upgradable"] = self.upgrade_packages
            if not utils.is_root() and utils.can_sudo() \
                    and not config.Prefs.emerge.pretend:
                self.setup_command('world', 'sudo -p "Password: " emerge --update' +
                        config.Prefs.emerge.get_string() + 'world')
            else:
                self.setup_command('world', "emerge --update" +
                        config.Prefs.emerge.get_string() + 'world')
        else:
            # load the upgrades view to select which packages
            self.widget["view_filter"].set_active(SHOW_UPGRADE)
        # get rid of the dialog
        self.upgrades_loaded_dialog.destroy()

    def load_descriptions_list(self):
        """ Load a list of all descriptions for searching """
        self.desc_dialog = SingleButtonDialog(_("Please Wait!"),
                self.mainwindow,
                _("Loading package descriptions..."),
                self.desc_dialog_response, "_Cancel", True)
        debug.dprint("MAINWINDOW: load_descriptions_list(); starting self.desc_thread")
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
        #debug.dprint(tmp_search_term)
        if tmp_search_term:
            # change view and statusbar so user knows it's searching.
            # This won't actually do anything unless we thread the search.
            self.loaded["Search"] = True # or else v_f_c() tries to call package_search again
            self.widget["view_filter"].set_active(SHOW_SEARCH)
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
            self.pkg_list["Search"][search_term] = package_list
            self.pkg_count["Search"][search_term] = count
            #Add the current search item & select it
            self.category_view.populate(self.pkg_list["Search"].keys(), True, self.pkg_count["Search"])
            iter = self.category_view.model.get_iter_first()
            while iter != None:
                if self.category_view.model.get_value(iter, 1) == search_term:
                    selection = self.category_view.get_selection()
                    selection.select_iter(iter)
                    break
                iter = self.category_view.model.iter_next(iter)
            self.package_view.populate(package_list)
            if count == 1: # then select it
                self.current_pkg_name["Search"] = package_list.keys()[0]
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
        debug.dprint("MAINWINDOW: refresh()")
        mode = self.widget["view_filter"].get_active()
        if mode in [SHOW_SEARCH]:
            self.category_changed(self.current_search)
        else:
            self.category_changed(self.current_cat_name[INDEX_TYPES[mode]])

    def category_changed(self, category):
        """Catch when the user changes categories."""
        mode = self.widget["view_filter"].get_active()
        # log the new category for reloads
        if mode not in [SHOW_SEARCH]: #, SHOW_UPGRADE, SHOW_SETS]:
            self.current_cat_name[INDEX_TYPES[mode]] = category
            self.current_cat_cursor[INDEX_TYPES[mode]] = self.category_view.get_cursor()
        #~ elif mode == SHOW_UPGRADE:
            #~ self.current_cat_name["All_Installed"]["Upgradable"] = category
            #~ self.current_upgrade_cursor = self.category_view.get_cursor()
        elif mode in [SHOW_SEARCH]:
            self.current_search = category
            self.current_search_cursor = self.category_view.get_cursor()
        if not self.reload:
            self.current_pkg_cursor["All"] = None
            self.current_pkg_cursor["Installed"] = None
        #debug.dprint("Category cursor = " +str(self.current_cat_cursor["All_Installed"]))
        #debug.dprint("Category = " + category)
        #debug.dprint(self.current_cat_cursor["All_Installed"][0])#[1])
        if self.current_cat_cursor[INDEX_TYPES[mode]]:
            cursor = self.current_cat_cursor[INDEX_TYPES[mode]][0]
            if cursor and len(cursor) > 1:
                sub_row = cursor[1] == None
            else:
                sub_row = False
        else:
            cursor = None
            sub_row = False
        self.clear_package_detail()
        if mode == SHOW_SEARCH:
            packages = self.pkg_list["Search"][category]
            #if len(packages) == 1: # then select it
            #    self.current_pkg_name["Search"] = packages.values()[0].get_name()
            #self.package_view.populate(packages, self.current_pkg_name["Search"])
            # if search was a package name, select that one
            # (searching for 'python' for example would benefit)
            self.package_view.populate(packages, category)
        elif not category or sub_row: #(self.current_cat_cursor["All_Installed"][0][1] == None):
            debug.dprint('MAINWINDOW: category_changed(); category=False or self.current_cat_cursor[' + INDEX_TYPES[mode] + '][0][1]==None')
            packages = None
            self.current_pkg_name[INDEX_TYPES[mode]] = None
            self.current_pkg_cursor[INDEX_TYPES[mode]] = None
            self.current_pkg_path[INDEX_TYPES[mode]] = None
            #self.package_view.set_view(PACKAGES)
            self.package_view.populate(None)
        elif mode in [SHOW_UPGRADE, SHOW_DEPRECATED, SHOW_SETS]:
            packages = self.pkg_list[INDEX_TYPES[mode]][category]
            self.package_view.populate(packages, self.current_pkg_name[INDEX_TYPES[mode]])
        elif mode == SHOW_ALL:
            packages = db.db.categories[category]
            self.package_view.populate(packages, self.current_pkg_name["All"])
        elif mode == SHOW_INSTALLED:
            packages = db.db.installed[category]
            self.package_view.populate(packages, self.current_pkg_name["Installed"])
        else:
            raise Exception("The programmer is stupid. Unknown category_changed() mode");

    def clear_package_detail(self):
        self.packagebook.clear_notebook()
        self.set_package_actions_sensitive(False)


    def package_changed(self, package):
        """Catch when the user changes packages."""
        debug.dprint("MAINWINDOW: package_changed()")
        if not package or package.full_name == _("None"):
            self.clear_package_detail()
            self.current_pkg_name[INDEX_TYPES[0]] = ''
            self.current_pkg_cursor[INDEX_TYPES[0]] = self.package_view.get_cursor()
            self.current_pkg_path[INDEX_TYPES[0]] = self.current_pkg_cursor[INDEX_TYPES[0]][0]
            return
        # log the new package for db reloads
        x = self.widget["view_filter"].get_active()
        self.current_pkg_name[INDEX_TYPES[x]] = package.get_name()
        self.current_pkg_cursor[INDEX_TYPES[x]] = self.package_view.get_cursor()
        debug.dprint("MAINWINDOW: package_changed(); new cursor = " + str(self.current_pkg_cursor[INDEX_TYPES[x]]))
        self.current_pkg_path[INDEX_TYPES[x]] = self.current_pkg_cursor[INDEX_TYPES[x]][0]
         #debug.dprint("Package name= %s, cursor = " %str(self.current_pkg_name[INDEX_TYPES[x]]))
        #debug.dprint(self.current_pkg_cursor[INDEX_TYPES[x]])
        # the notebook must be sensitive before anything is displayed
        # in the tabs, especially the deps_view
        self.set_package_actions_sensitive(True, package)
        self.packagebook.set_package(package)

    def view_filter_changed(self, widget):
        """Update the treeviews for the selected filter"""
        #debug.dprint("MAINWINDOW: view_filter_changed()")
        x = widget.get_active()
        debug.dprint("MAINWINDOW: view_filter_changed(); x = %d" %x)
        self.update_statusbar(x)
        cat_scroll = self.wtree.get_widget("category_scrolled_window")
        self.category_view.set_search(False)
        self.clear_package_detail()
        cat = None #self.current_cat_name["All_Installed"]
        pack = None #self.current_pkg_name["All_Installed"]
        sort_categories = False

        if x in (SHOW_INSTALLED, SHOW_ALL):
            if x == SHOW_ALL:
                items = db.db.categories.keys()
                count = db.db.pkg_count
            else:
                items = db.db.installed.keys()
                count = db.db.installed_pkg_count
            self.category_view.populate(items, True, count)
            cat_scroll.show()
            debug.dprint("MAINWINDOW: view_filter_changed(); reset package_view")
            self.package_view.set_view(PACKAGES)
            debug.dprint("MAINWINDOW: view_filter_changed(); init package_view")
            self.package_view._init_view()
            #debug.dprint("MAINWINDOW: view_filter_changed(); clear package_view")
            #self.package_view.clear()
            cat = self.current_cat_name[INDEX_TYPES[x]]
            pack = self.current_pkg_name[INDEX_TYPES[x]]
            debug.dprint("MAINWINDOW: view_filter_changed(); reselect category & package")
            #self.select_category_package(cat, pack, x)
        elif x == SHOW_SEARCH:
            self.category_view.set_search(True)
            if not self.loaded[INDEX_TYPES[x]]:
                self.set_package_actions_sensitive(False, None)
                self.category_view.populate(self.pkg_list[INDEX_TYPES[x]].keys(), True, self.pkg_count[INDEX_TYPES[x]])
                self.package_search(None)
                self.loaded[INDEX_TYPES[x]] = True
            else:
                self.category_view.populate(self.pkg_list[INDEX_TYPES[x]].keys(), True, self.pkg_count[INDEX_TYPES[x]])
            cat_scroll.show();
            debug.dprint("MAIN: Showing search results")
            self.package_view.set_view(SEARCH)
            cat = self.current_search
            pack = self.current_pkg_name[INDEX_TYPES[x]]
            #self.select_category_package(cat, pack, x)
        elif x in [SHOW_UPGRADE, SHOW_DEPRECATED, SHOW_SETS]:
            debug.dprint("MAINWINDOW: view_filter_changed(); '" + INDEX_TYPES[x] + "' selected")
            cat_scroll.show();
            sort_categories = True  # all need to be sorted for them to be displayed in the tree correctly
            if x == SHOW_UPGRADE:
                self.package_view.set_view(UPGRADABLE)
            elif x == SHOW_DEPRECATED:
                self.package_view.set_view(DEPRECATED)
            else:
                self.package_view.set_view(SETS)
            if not self.loaded[INDEX_TYPES[x]]:
                debug.dprint("MAINWINDOW: view_filter_changed(); calling load_reader_list('" + INDEX_TYPES[x] + "') reader_running = %s ********************************" %self.reader_running)
                self.load_reader_list(INDEX_TYPES[x])
                self.package_view.clear()
                self.category_view.clear()
                debug.dprint("MAINWINDOW: view_filter_changed(); back from load_reader_list('" + INDEX_TYPES[x] + "')")
            else:
                debug.dprint("MAINWINDOW: view_filter_changed(); calling category_view.populate() with categories:" + str(self.pkg_list[INDEX_TYPES[x]].keys()))
                self.category_view.populate(self.pkg_list[INDEX_TYPES[x]].keys(), sort_categories, self.pkg_count[INDEX_TYPES[x]])
            #self.package_view.set_view(UPGRADABLE)
            debug.dprint("MAINWINDOW: view_filter_changed(); init package_view")
            self.package_view._init_view()
            #debug.dprint("MAINWINDOW: view_filter_changed(); clear package_view")
            #self.package_view.clear()
            cat = self.current_cat_name[INDEX_TYPES[x]]
            pack = self.current_pkg_name[INDEX_TYPES[x]]
        #~ elif x == SHOW_SETS:
            #~ debug.dprint("MAINWINDOW: view_filter_changed(); Sets selected")
            #~ cat = None #self.current_cat_name["All_Installed"]
            #~ pack = None #self.current_pkg_name["All_Installed"]
            #~ pass

        debug.dprint("MAINWINDOW: view_filter_changed(); reselect category & package (maybe)")
        if cat != None: # and pack != None:
            self.select_category_package(cat, pack, x)
        # clear the notebook tabs
        #self.clear_package_detail()
        #if self.last_view_setting != x:
        debug.dprint("MAINWINDOW: view_filter_changed(); last_view_setting " + str(self.last_view_setting) + " changed: x = " + str(x))
        self.last_view_setting = x
        #self.current_cat_name["All_Installed"] = None
        #self.category_view.last_category = None
        #self.current_cat_cursor["All_Installed"] = None
        #self.current_pkg_cursor["All_Installed"] = None
    
    def select_category_package(self, cat, pack, x):
        debug.dprint("MAINWINDOW: select_category_package(): %s/%s, x = %s" % (cat, pack,INDEX_TYPES[x]))
        model = self.category_view.get_model()
        iter = model.get_iter_first()
        catpath = None
        if  cat and '-' in cat: # x in [SHOW_INSTALLED, SHOW_ALL, SHOW_UPGRADE] and
            # find path of category
            catmaj, catmin = cat.split("-",1)
            debug.dprint("catmaj, catmin = %s, %s" % (catmaj, catmin))
            while iter:
                debug.dprint("value at iter %s: %s" % (iter, model.get_value(iter, 0)))
                if catmaj == model.get_value(iter, 0):
                    kids = model.iter_n_children(iter)
                    while kids: # this will count backwards, but hey so what
                        kiditer = model.iter_nth_child(iter, kids - 1)
                        if catmin == model.get_value(kiditer, 0):
                            catpath = model.get_path(kiditer)
                            break
                        kids -= 1
                    if catpath:
                        debug.dprint("found value at iter %s: %s" % (iter, model.get_value(kiditer, 0)))
                        break
                iter = model.iter_next(iter)
        elif cat: #elif x in [SHOW_SEARCH, SHOW_DEPRECATED, SHOW_SETS]:
            while iter:
                if cat == model.get_value(iter, 0):
                    catpath = model.get_path(iter)
                    break
                iter = model.iter_next(iter)
        #    catpath = 'Sure, why not?'
        else: debug.dprint("MAINWINDOW: select_category_package(): bad category?")
        if catpath:
            self.category_view.expand_to_path(catpath)
            self.category_view.last_category = None # so it thinks it's changed
            self.category_view.set_cursor(catpath)
            # now reselect whatever package we had selected
            model = self.package_view.get_model()
            iter = model.get_iter_first()
            path = None
            while iter and pack:
                #debug.dprint("value at iter %s: %s" % (iter, model.get_value(iter, 0)))
                if model.get_value(iter, 0).split('/')[-1] == pack:
                    path = model.get_path(iter)
                    self.package_view._last_selected = None
                    self.package_view.set_cursor(path)
                    break
                iter = model.iter_next(iter)
            if not path:
                debug.dprint("MAINWINDOW: select_category_package(): no package found")
                self.clear_package_detail()
        else:
            debug.dprint("MAINWINDOW: select_category_package(): no category path found")
            self.clear_package_detail()

    def load_reader_list(self, reader):
        self.reader_progress = 1
        # package list is not loaded, create dialog and load them
        self.set_statusbar2(_("Generating '%s' packages list...") %READER_NAMES[reader])
        # create reader thread for loading the packages
        if self.reader_running:
            debug.dprint("MAINWINDOW: load_reader_list(); thread already running!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return
        debug.dprint("MAINWINDOW: load_reader_list(); starting thread")
        if reader == "Deprecated":
            self.reader = DeprecatedReader(db.db.installed.items())
        elif reader == "Upgradable":
            self.reader = UpgradableListReader(db.db.installed.items())
        elif reader == "Sets":
            self.reader = SetListReader()

        self.reader.start()
        self.reader_running = True
        debug.dprint("MAINWINDOW: load_reader_list(); reader_running set to True")
        self.build_deps = False
        # add a timeout to check if thread is done
        gobject.timeout_add(200, self.update_reader_thread)
        self.set_cancel_btn(ON)


    def wait_dialog_response(self, widget, response):
        """ Get a response from the wait dialog """
        if response == 0:
            # terminate the thread
            self.reader.please_die()
            self.reader.join()
            # get rid of the dialog
            self.wait_dialog.destroy()

    def update_reader_thread(self):
        """ Find out if thread is finished """
        # needs error checking perhaps...
        reader_type = self.reader.reader_type
        if self.reader.done:
            debug.dprint("MAINWINDOW: update_reader_thread(): self.reader.done detected")
            self.reader.join()
            self.reader_running = False
            self.progress_done(True)
            if self.reader.cancelled:
                return False
            debug.dprint("MAINWINDOW: update_reader_thread(): reader_type = " + reader_type)
            if reader_type in ["Upgradable", "Deprecated", "Sets"]:
                self.pkg_list[reader_type] = self.reader.pkg_dict
                self.pkg_count[reader_type] = self.reader.pkg_count
                debug.dprint("MAINWINDOW: update_reader_thread(): pkg_count = " + str(self.pkg_count))
                self.loaded[reader_type] = True
                self.view_filter_changed(self.widget["view_filter"])
                if self.loaded_callback[reader_type]:
                    self.loaded_callback[reader_type](None)
                    self.loaded_callback[reader_type] = None
                else:
                    if self.last_view_setting == SHOW_UPGRADE:
                        self.package_view.set_view(UPGRADABLE)
                        self.packagebook.summary.update_package_info(None)
                        #self.wtree.get_widget("category_scrolled_window").hide()
                    elif self.last_view_setting == SHOW_DEPRECATED:
                        self.package_view.set_view(DEPRECATED)
                        self.packagebook.summary.update_package_info(None)
                        #self.wtree.get_widget("category_scrolled_window").hide()
                    elif self.last_view_setting == SHOW_SETS:
                        self.package_view.set_view(SETS)
                        self.packagebook.summary.update_package_info(None)
                return False
        elif self.reader.progress < 2:
            # Still building system package list nothing to do
            pass
        else:
            # stsatubar hack, should probably be converted to use a Dispatcher callback
            if self.reader.progress >= 2 and self.reader_progress == 1:
                self.set_statusbar2(_("Searching for '%s' packages...") %READER_NAMES[self.reader.reader_type])
                self.reader_progress = 2
            if self.reader_running:
                try:
                    if self.build_deps:
                        count = 0
                        for key in self.reader.pkg_count:
                            count += self.reader.pkg_count[key]
                        fraction = count / float(self.reader.pkg_dict_total)
                        self.progressbar.set_text(str(int(fraction * 100)) + "%")
                        self.progressbar.set_fraction(fraction)
                    else:
                        fraction = self.reader.count / float(db.db.installed_count)
                        self.progressbar.set_text(str(int(fraction * 100)) + "%")
                        self.progressbar.set_fraction(fraction)
                        if fraction == 1:
                            self.build_deps = True
                            self.set_statusbar2(_("Building Package List"))
                except Exception, e:
                    debug.dprint("MAINWINDOW: update_reader_thread(): Exception: %s" % e)
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
                debug.dprint("MAINWINDOW: attempt to update status bar with no db assigned")
            else:
                text = (_("%(pack)d packages in %(cat)d categories")
                        % {'pack':len(db.db.list), 'cat':len(db.db.categories)})
        elif mode == SHOW_INSTALLED:
            if not db.db:
                debug.dprint("MAINWINDOW: attempt to update status bar with no db assigned")
            else:
                text = (_("%(pack)d packages in %(cat)d categories") 
                        % {'pack':db.db.installed_count, 'cat':len(db.db.installed)})
        elif mode in [SHOW_SEARCH, SHOW_DEPRECATED, SHOW_SETS]:
            text = '' #(_("%d matches found") % self.package_view.search_model.size)

        elif mode == SHOW_UPGRADE:
            if not self.reader:
                debug.dprint("MAINWINDOW: attempt to update status bar with no reader thread assigned")
            else:
                text = '' #(_("%(world)d world, %(deps)d dependencies")
                           # % {'world':self.reader.pkg_count["World"], 'deps':self.reader.pkg_count["Dependencies"]})

        self.set_statusbar2(self.status_root + text)

    def set_package_actions_sensitive(self, enabled, package = None):
        """Sets package action buttons/menu items to sensitive or not"""
        #debug.dprint("MAINWINDOW: set_package_actions_sensitive(%d)" %enabled)
        self.widget["emerge_package1"].set_sensitive(enabled)
        self.widget["adv_emerge_package1"].set_sensitive(enabled)
        self.widget["unmerge_package1"].set_sensitive(enabled)
        self.widget["btn_emerge"].set_sensitive(enabled)
        self.widget["btn_adv_emerge"].set_sensitive(enabled)
        if not enabled or enabled and package.get_installed():
            #debug.dprint("MAINWINDOW: set_package_actions_sensitive() setting unmerge to %d" %enabled)
            self.widget["btn_unmerge"].set_sensitive(enabled)
            self.widget["unmerge_package1"].set_sensitive(enabled)
        else:
            #debug.dprint("MAINWINDOW: set_package_actions_sensitive() setting unmerge to %d" %(not enabled))
            self.widget["btn_unmerge"].set_sensitive(not enabled)
            
            self.widget["unmerge_package1"].set_sensitive(not enabled)
        self.packagebook.notebook.set_sensitive(enabled)

    def size_update(self, widget, event):
        #debug.dprint("MAINWINDOW: size_update(); called.")
        """ Store the window and pane positions """
        config.Prefs.main.width = event.width
        config.Prefs.main.height = event.height
        pos = widget.get_position()
        # note: event has x and y attributes but they do not give the same values as get_position().
        config.Prefs.main.xpos = pos[0]
        config.Prefs.main.ypos = pos[1]

    def open_log(self, widget):
        """ Open a log of a previous emerge in a new terminal window """
        newterm = ProcessManager(utils.environment(), True)
        newterm.do_open(widget)

    def custom_run(self, widget):
        """ Run a custom command in the terminal window """
        #debug.dprint("MAINWINDOW: entering custom_run")
        #debug.dprint(config.Prefs.run_dialog.history)
        get_command = RunDialog(self.setup_command, run_anyway=True)

    def re_init_portage(self, *widget):
        """re-initializes the imported portage modules in order to see changines in any config files
        e.g. /etc/make.conf USE flags changed"""
        portage_lib.reload_portage()
        ##portage_lib.reset_use_flags()
##        if  self.current_pkg_cursor["All_Installed"] != None and self.current_pkg_cursor["All_Installed"][0]: # should fix a type error in set_cursor; from pycrash report
##            # reset _last_selected so it thinks this package is new again
##            self.package_view._last_selected = None
##            # re-select the package
##            self.package_view.set_cursor(self.current_pkg_cursor["All_Installed"][0],
##            self.current_pkg_cursor["All_Installed"][1])
        self.view_filter_changed(self.widget["view_filter"])

    def quit(self, widget):
        if not self.confirm_delete():
            self.goodbye(None)
        return

    def goodbye(self, widget):
        """Main window quit function"""
        debug.dprint("MAINWINDOW: goodbye(); quiting now")
        try: # for >=pygtk-2.3.94
            debug.dprint("MAINWINDOW: gtk.main_quit()")
            gtk.main_quit()
        except: # use the depricated function
            debug.dprint("MAINWINDOW: gtk.mainquit()")
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
            debug.dprint("TERMINAL: kill(); not killing")
            return True
        #self.process_manager.confirm = False
        if self.process_manager.kill_process(None, False):
            debug.dprint("MAINWINDOW: process killed, destroying window")
            self.process_manager.allow_delete = True
            self.process_manager.window.hide()
        return False

