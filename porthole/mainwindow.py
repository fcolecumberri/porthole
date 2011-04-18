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
_id = datetime.datetime.now().microsecond
print "MAINWINDOW: id initialized to ", _id

import pygtk
pygtk.require("2.0") # make sure we have the right version
import gtk, gtk.glade, gobject
import os
from gettext import gettext as _

from porthole.utils import utils, debug
from porthole import config
from porthole import backends
PMS_LIB = backends.portage_lib
#World = PMS_LIB.settings.get_world
from porthole.views.package import PACKAGES, SEARCH, \
        UPGRADABLE, DEPRECATED, SETS
from porthole.utils.dispatcher import Dispatcher
from porthole.dialogs.simple import SingleButtonDialog
from porthole.readers.upgradeables import UpgradableListReader
from porthole.readers.deprecated import DeprecatedReader
from porthole.readers.sets import SetListReader
from porthole import db
#from timeit import Timer

from porthole.mwsupport.status import StatusHandler
from porthole.mwsupport.plugin import PluginHandler


from porthole.mwsupport.constants import (INDEX_TYPES, SHOW_ALL,
    SHOW_INSTALLED, SHOW_SEARCH, SHOW_UPGRADE, SHOW_DEPRECATED, SHOW_SETS,
    ON, OFF, READER_NAMES)



class MainWindow(PluginHandler):
    """Main Window class to setup and manage main window interface."""
    def __init__(self) :
        debug.dprint("MAINWINDOW: process id = %d ****************"
            %os.getpid())

        # set unfinished items to not be sensitive
        #self.wtree.get_widget("contents2").set_sensitive(False)
        # self.wtree.get_widget("btn_help").set_sensitive(False)


        # Initialize our subclasses
        PluginHandler.__init__(self)

        self.status = StatusHandler(
            self.wtree.get_widget("statusbar2"),
            self.wtree.get_widget("progressbar1"),
            self.category_view,
            self.package_view,
            self.current_pkg_path,
            self.current_pkg_cursor,
            self.plugin_views
            )

        # get an empty tooltip
        ##self.synctooltip = gtk.Tooltips()
        self.sync_tip = _(
            " Synchronise Package Database \n The last sync was done:\n")
        # set the sync label to the saved one set in the options
        self.widget["btn_sync"].set_label(config.Prefs.globals.Sync_label)
        self.widget["view_refresh"].set_sensitive(False)
        # restore last window width/height
        if config.Prefs.main.xpos and config.Prefs.main.ypos:
            self.mainwindow.move(config.Prefs.main.xpos,
                    config.Prefs.main.ypos)
        self.mainwindow.resize(config.Prefs.main.width,
                config.Prefs.main.height)
        # connect gtk callback for window movement and resize events
        self.mainwindow.connect("configure-event", self.size_update)
        # restore maximized state and set window-state-event
        # handler to keep track of it
        if config.Prefs.main.maximized:
            self.mainwindow.maximize()
        self.mainwindow.connect("window-state-event",
                self.on_window_state_event)
        # move horizontal and vertical panes
        #debug.dprint("MAINWINDOW: __init__() before hpane; " +
            #"%d, vpane; %d"
            #%(config.Prefs.main.hpane, config.Prefs.main.vpane))
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
        self.status.set_statusbar2("Starting")
        # set if we are root or not
        self.is_root = utils.is_root()
        debug.dprint("MAINWINDOW: __init__(); is_root = " + str(self.is_root))
        if config.Prefs.main.show_nag_dialog:
            # let the user know if he can emerge or not
            self.check_for_root()
        self.toolbar_expander = self.wtree.get_widget("toolbar_expander")
        # This should be set in the glade file, but doesn't seem to work ?
        self.toolbar_expander.set_expand(True)
        # populate the view_filter menu
        self.widget["view_filter_list"] = gtk.ListStore(str)
        for i in [_("All Packages"), _("Installed Packages"),
                    _("Search Results"), _("Upgradable Packages"),
                    _("Deprecated Packages"), _("Sets")]:
            self.widget["view_filter_list"].append([i])
        self.widget["view_filter"].set_model(self.widget["view_filter_list"])
        self.widget["view_filter"].set_active(SHOW_ALL)
        self.setup_plugins()

        callbacks = {
            "action_callback" : self.action_callback,
            "re_init_portage" : self.re_init_portage,
            "set_package_actions_sensitive" : self.set_package_actions_sensitive
        }
        self.assign_packagebook(self.wtree,
            callbacks, self.plugin_package_tabs)
        # initialize our data
        self.init_data()
        self.search_dispatcher = Dispatcher(self.search_done)
        debug.dprint("MAINWINDOW: Showing main window")
        self.mainwindow.show_all()
        if self.is_root:
            # hide warning toolbar widget
            debug.dprint("MAINWINDOW: __init__(); hiding btn_root_warning")
            self.wtree.get_widget("btn_root_warning").hide()


    def init_data(self):
        """initialize the db and anything else related to package selection"""
        # set things we can't do unless a package is selected to not sensitive
        self.set_package_actions_sensitive(False)
        debug.dprint("MAINWINDOW: init_data(); Initializing data")
        # set status
        #self.status.set_statusbar(_("Obtaining package list "))
        self.status.status_root = _("Loading database: ")
        self.status.set_statusbar2(_("Initializing database. Please wait..."))
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
        for i in INDEX_TYPES:
            self.current_cat_name[i] = None
            self.current_cat_cursor[i] = None
            self.current_pkg_name[i] = None
            self.current_pkg_cursor[i] = None
            self.current_pkg_path[i] = None
            if i not  in ["All", "Installed", "Binpkgs"]:
                # init pkg lists, counts
                self.pkg_list[i] =  {}
                self.pkg_count[i] =  {}
                self.loaded[i] = False
            if i in ["Upgradable", "Deprecated", "Sets", "Binpkgs"]:
                self.loaded_callback[i] = None

        # next add any index names that need to be reset on a reload
        self.loaded_resets = ["Search", "Deprecated", "Binpkgs"]
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
        """initiatiate a full db reload"""
        debug.dprint("MAINWINDOW: reload_db() callback")
        self.status.progress_done()
        self.set_cancel_btn(OFF)
        for x in self.loaded_resets:
            self.loaded[x] = False
        for i in ["All", "Installed", "Binpkgs"]:
            self.current_pkg_path[i] = None
        self.current_pkg_cursor["Search"] = None
        # test to reset portage
        #PMS_LIB.reload_portage()
        PMS_LIB.settings.reload_world()
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
        #self.status.set_statusbar(_("Obtaining package list "))
        self.status.status_root = _("Reloading database")
        self.status.set_statusbar2(self.status.status_root)
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

    def emerge_setting_set(self, widget, option='null'):
        """Set whether or not we are going to use an emerge option"""
        debug.dprint("MAINWINDOW: emerge_setting_set(%s)" %option)
        debug.dprint("MAINWINDOW: emerge_setting_set; " +
            str(widget) + " " + option)
        setattr(config.Prefs.emerge, option, widget.get_active())
        #config.Prefs.emerge.oneshot = widget.get_active()

    def search_set(self, widget):
        """Set whether or not to search descriptions"""
        config.Prefs.main.search_desc = widget.get_active()

    def emerge_btn(self, widget, sudo=False):
        """callback for the emerge toolbutton and menu entries"""
        if not self.process_selection("emerge"):
            package = utils.get_treeview_selection(self.package_view, 2)
            self.emerge_package(package, sudo)

    def adv_emerge_btn(self, *widget):
        """Advanced emerge of the currently selected package."""
        package = utils.get_treeview_selection(self.package_view, 2)
        self.adv_emerge_package(package)

    def unmerge_btn(self, widget, sudo=False):
        """callback for the Unmerge button and menu entry to
        unmerge the currently selected package."""
        if not self.process_selection("emerge --unmerge"):
            package = utils.get_treeview_selection(self.package_view, 2)
            self.unmerge_package(package, sudo)

    def on_cancel_btn(self, *widget):
        """cancel button callback function"""
        debug.dprint("MAINWINDOW: on_cancel_btn() callback")
        # terminate the thread
        self.reader.please_die()
        self.reader.join()
        self.status.progress_done()
        self.set_cancel_btn(OFF)

    def on_window_state_event(self, widget, event):
        """Handler for window-state-event gtk callback.
        Just checks if the window is maximized or not"""
        if widget is not self.mainwindow:
            return False
        debug.dprint("MAINWINDOW: on_window_state_event(); event detected")
        if gtk.gdk.WINDOW_STATE_MAXIMIZED & event.new_window_state:
            config.Prefs.main.maximized = True
        else:
            config.Prefs.main.maximized = False

    def on_pane_notify(self, pane, gparamspec):
        """callback function for the pane re-size signal
        stores the new settings for next time"""
        if gparamspec.name == "position":
            # save hpane, vpane positions
            config.Prefs.main.hpane = self.hpane.get_position()
            config.Prefs.main.vpane = self.vpane.get_position()

    def upgrades_loaded_dialog_response(self, widget, response):
        """ Get and parse user's response """
        if response == 0: # Yes was selected; upgrade all
            #self.load_upgrades_list()
            #self.loaded_callback["Upgradable"] = self.upgrade_packages
            if not utils.is_root() and utils.can_sudo() \
                    and not config.Prefs.emerge.pretend:
                self.setup_command('world',
                        'sudo -p "Password: " emerge --update' +
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
        debug.dprint("MAINWINDOW: load_descriptions_list(); " +
            "starting self.desc_thread")
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
                self.desc_dialog.progbar.set_text(
                    str(int(fraction * 100)) + "%")
                self.desc_dialog.progbar.set_fraction(fraction)
        return True

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
        self.status.update_statusbar(SHOW_SEARCH)
        self.pkg_list["Search"][search_term] = package_list
        self.pkg_count["Search"][search_term] = count
        #Add the current search item & select it
        self.category_view.populate(self.pkg_list["Search"].keys(), True,
            self.pkg_count["Search"])
        _iter = self.category_view.model.get_iter_first()
        while _iter != None:
            if self.category_view.model.get_value(_iter, 1) == search_term:
                selection = self.category_view.get_selection()
                selection.select_iter(_iter)
                break
            _iter = self.category_view.model.iter_next(_iter)
        self.package_view.populate(package_list)
        if count == 1: # then select it
            self.current_pkg_name["Search"] = package_list.keys()[0]
        self.category_view.last_category = search_term
        self.category_changed(search_term)

    def view_filter_changed(self, widget):
        """Update the treeviews for the selected filter"""
        #debug.dprint("MAINWINDOW: view_filter_changed()")
        myview = widget.get_active()
        debug.dprint("MAINWINDOW: view_filter_changed(); myview = %d" %myview)
        self.status.update_statusbar(myview, self.reader)
        cat_scroll = self.wtree.get_widget("category_scrolled_window")
        self.category_view.set_search(False)
        self.clear_package_detail()
        cat = None
        pack = None
        sort_categories = False

        if myview in self.plugin_views.keys():
            if self.plugin_view[myview]["package_view"]:
                self.chg_pkgview(self.plugin_view[myview]["package_view"])
            self.plugin_view[myview]["view_changed"]
        elif myview in (SHOW_INSTALLED, SHOW_ALL):
            self.chg_pkgview(self.package_view)
            if myview == SHOW_ALL:
                items = db.db.categories.keys()
                count = db.db.pkg_count
            else:
                items = db.db.installed.keys()
                count = db.db.installed_pkg_count
            self.category_view.populate(items, True, count)
            cat_scroll.show()
            debug.dprint("MAINWINDOW: view_filter_changed(); " +
                "reset package_view")
            self.package_view.set_view(PACKAGES)
            debug.dprint("MAINWINDOW: view_filter_changed(); " +
                "init package_view")
            self.package_view._init_view()
            #debug.dprint("MAINWINDOW: view_filter_changed(); " +
                #"clear package_view")
            #self.package_view.clear()
            cat = self.current_cat_name[INDEX_TYPES[myview]]
            pack = self.current_pkg_name[INDEX_TYPES[myview]]
            debug.dprint("MAINWINDOW: view_filter_changed(); " +
                "reselect category & package")
        elif myview == SHOW_SEARCH:
            self.chg_pkgview(self.package_view)
            self.category_view.set_search(True)
            if not self.loaded[INDEX_TYPES[myview]]:
                self.set_package_actions_sensitive(False, None)
                self.category_view.populate(
                    self.pkg_list[INDEX_TYPES[myview]].keys(),
                    True,
                    self.pkg_count[INDEX_TYPES[myview]])
                self.package_search(None)
                self.loaded[INDEX_TYPES[myview]] = True
            else:
                self.category_view.populate(
                    self.pkg_list[INDEX_TYPES[myview]].keys(),
                    True,
                    self.pkg_count[INDEX_TYPES[myview]])
            cat_scroll.show()
            debug.dprint("MAIN: Showing search results")
            self.package_view.set_view(SEARCH)
            cat = self.current_search
            pack = self.current_pkg_name[INDEX_TYPES[myview]]
        elif myview in [SHOW_UPGRADE, SHOW_DEPRECATED, SHOW_SETS]:
            debug.dprint("MAINWINDOW: view_filter_changed(); '" +
                INDEX_TYPES[myview] + "' selected")
            self.chg_pkgview(self.package_view)
            cat_scroll.show()
            # all need to be sorted for them to be
            # displayed in the tree correctly
            sort_categories = True
            if myview == SHOW_UPGRADE:
                self.package_view.set_view(UPGRADABLE)
            elif myview == SHOW_DEPRECATED:
                self.package_view.set_view(DEPRECATED)
            else:
                self.package_view.set_view(SETS)
            if not self.loaded[INDEX_TYPES[myview]]:
                debug.dprint("MAINWINDOW: view_filter_changed(); " +
                    "calling load_reader_list('" +
                    INDEX_TYPES[myview] +
                    "') reader_running = %s ********************************"
                    %self.reader_running)
                self.load_reader_list(INDEX_TYPES[myview])
                self.package_view.clear()
                self.category_view.clear()
                debug.dprint("MAINWINDOW: view_filter_changed(); " +
                    "back from load_reader_list('" + INDEX_TYPES[myview] + "')")
            else:
                debug.dprint("MAINWINDOW: view_filter_changed(); " +
                    "calling category_view.populate() with categories:" +
                    str(self.pkg_list[INDEX_TYPES[myview]].keys()))
                self.category_view.populate(
                    self.pkg_list[INDEX_TYPES[myview]].keys(),
                    sort_categories,
                    self.pkg_count[INDEX_TYPES[myview]])
            #self.package_view.set_view(UPGRADABLE)
            debug.dprint("MAINWINDOW: view_filter_changed(); init package_view")
            self.package_view._init_view()
            #debug.dprint("MAINWINDOW: view_filter_changed(); " +
                #"clear package_view")
            #self.package_view.clear()
            cat = self.current_cat_name[INDEX_TYPES[myview]]
            pack = self.current_pkg_name[INDEX_TYPES[myview]]
        #~ elif myview == SHOW_SETS:
            #~ debug.dprint("MAINWINDOW: view_filter_changed(); Sets selected")
            #~ cat = None #self.current_cat_name["All_Installed"]
            #~ pack = None #self.current_pkg_name["All_Installed"]
            #~ pass

        debug.dprint("MAINWINDOW: view_filter_changed(); " +
            "reselect category & package (maybe)")
        if cat != None: # and pack != None:
            self.select_category_package(cat, pack)
        # clear the notebook tabs
        #self.clear_package_detail()
        #if self.last_view_setting != myview:
        debug.dprint("MAINWINDOW: view_filter_changed(); last_view_setting " +
            str(self.last_view_setting) + " changed: myview = " + str(myview))
        self.last_view_setting = myview
        #self.current_cat_name["All_Installed"] = None
        #self.category_view.last_category = None
        #self.current_cat_cursor["All_Installed"] = None
        #self.current_pkg_cursor["All_Installed"] = None

    def load_reader_list(self, reader):
        """multipurpose loader can run a number of different
        reader threads"""
        self.reader_progress = 1
        # package list is not loaded, create dialog and load them
        self.status.set_statusbar2(_("Generating '%s' packages list...")
            %READER_NAMES[reader])
        # create reader thread for loading the packages
        if self.reader_running:
            debug.dprint("MAINWINDOW: load_reader_list(); " +
                "thread already running!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
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
        debug.dprint("MAINWINDOW: load_reader_list(); " +
            "reader_running set to True")
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
            debug.dprint("MAINWINDOW: update_reader_thread(): " +
                "self.reader.done detected")
            return self._reader_done(reader_type)
        elif self.reader.progress < 2:
            # Still building system package list nothing to do
            pass
        else:
            # statusbar hack,
            # should probably be converted to use a Dispatcher callback
            if self.reader.progress >= 2 and self.reader_progress == 1:
                self.status.set_statusbar2(_("Searching for '%s' packages...")
                    %READER_NAMES[self.reader.reader_type])
                self.reader_progress = 2
            if self.reader_running:
                try:
                    if self.build_deps:
                        count = 0
                        for key in self.reader.pkg_count:
                            count += self.reader.pkg_count[key]
                        fraction = count / float(self.reader.pkg_dict_total)
                        self.status.progressbar.set_text(
                            str(int(fraction * 100)) + "%")
                        self.status.progressbar.set_fraction(fraction)
                    else:
                        fraction = \
                            self.reader.count / float(db.db.installed_count)
                        self.status.progressbar.set_text(
                            str(int(fraction * 100)) + "%")
                        self.status.progressbar.set_fraction(fraction)
                        if fraction == 1:
                            self.build_deps = True
                            self.status.set_statusbar2(_("Building Package List"))
                except Exception, _error:
                    debug.dprint("MAINWINDOW: update_reader_thread(): " +
                        "Exception: %s" % _error)
        return True

    def update_db_read(self, args): # extra args for dispatcher callback
        """Update the statusbar according to the number of packages read."""
        #debug.dprint("StatusHandler: update_db_read()")
        if args["done"] == False:
            self._update_db_statusbar(args)
        elif args['db_thread_error']:
            # todo: display error dialog instead
            self.status.set_statusbar2(args['db_thread_error'].decode('ascii',
                    'replace'))
            return False  # disconnect from timeout
        else: # args["done"] == True - db_thread is done
            self._update_db_done()
        #debug.dprint("StatusHandler: returning from update_db_read() " +
            #"count=%d dbtime=%d"  %(count, self.dbtime))
        return True

    def _update_db_statusbar(self, args):
        """update the statusbar on progress"""
        count = args["nodecount"]
        if count > 0:
            self.status.set_statusbar2(_("%(base)s: %(count)i packages read")
                        % {'base':self.status.status_root, 'count':count})
        try:
            fraction = min(1.0, max(0,
                    (count / float(args["allnodes_length"]))))
            self.status.progressbar.set_text(str(int(fraction * 100)) + "%")
            self.status.progressbar.set_fraction(fraction)
        except:
            pass


    def _update_db_done(self):
        """performs the finalizing and cleanup after the
        db reader is finished"""
        self.status.progress(text="100%", fraction=1.0)
        self.status.set_statusbar2(_("%(base)s: Populating tree")
                % {'base':self.status.status_root})
        self.status.update_statusbar(SHOW_ALL)
        debug.dprint("StatusHandler: _update_db_done(); " +
            "setting menubar,toolbar,etc to sensitive...")
        for x in ["menubar", "toolbar", "view_filter", "search_entry",
                    "btn_search", "view_refresh"]:
            self.wtree.get_widget(x).set_sensitive(True)
        if self.plugin_manager and not self.plugin_manager.plugins:
            # no plugins
            self.wtree.get_widget("plugin_settings").set_sensitive(False)
        # make sure we search again if we reloaded!
        mode = self.widget["view_filter"].get_active()
        debug.dprint("StatusHandler: _update_db_done() mode = " + str(mode) +
                ' type = ' + str(type(mode)))
        if  mode in [SHOW_SEARCH]:
            #debug.dprint("StatusHandler: _update_db_done()... Search view")
            # update the views by calling view_filter_changed
            self.view_filter_changed(self.widget["view_filter"])
            # reset the upgrades list if it is loaded and not being viewed
            self.loaded["Upgradable"] = False
            if self.reload:
                # reset _last_selected so it
                # thinks this package is new again
                self.package_view._last_selected = None
                if self.current_pkg_cursor["Search"] != None \
                        and self.current_pkg_cursor["Search"][0]:
                        # should fix a type error in set_cursor
                    # re-select the package
                    self.package_view.set_cursor(
                            self.current_pkg_cursor["Search"][0],
                            self.current_pkg_cursor["Search"][1])
        elif self.reload and mode in [SHOW_ALL, SHOW_INSTALLED]:
            #debug.dprint("StatusHandler: _update_db_done()... self.reload=" +
                    #"True ALL or INSTALLED view")
            # reset _last_selected so it thinks this category is new again
            self.category_view._last_category = None
            #debug.dprint("StatusHandler: _update_db_done(); " +
                #"re-select the category: " +
                #"self.current_cat_cursor["All_Installed"] =")
            #debug.dprint(self.current_cat_cursor["All_Installed"])
            #debug.dprint(type(self.current_cat_cursor["All_Installed"]))
            if (self.current_cat_cursor[INDEX_TYPES[mode]] != None) \
                    and \
                    (self.current_cat_cursor[INDEX_TYPES[mode]] != \
                    [None, None]):
                # re-select the category
                try:
                    self.category_view.set_cursor(
                        self.current_cat_cursor[INDEX_TYPES[mode]][0],
                        self.current_cat_cursor[INDEX_TYPES[mode]][1])
                except:
                    debug.dprint("StatusHandler: _update_db_done(); error " +
                        "converting self.current_cat_cursor[" + str(mode) +
                        "][]: %s"
                        %str(self.current_cat_cursor[INDEX_TYPES[mode]]))
            #~ #debug.dprint("StatusHandler: _update_db_done(); " +
                #"reset _last_selected so it thinks this package is new again")
            self.package_view._last_selected = None
            #~ #debug.dprint("StatusHandler: _update_db_done(); " +
                #~ "re-select the package")
            # re-select the package
            if self.current_pkg_path[INDEX_TYPES[mode]] != None:
                if self.current_pkg_cursor[INDEX_TYPES[mode]] != None and \
                        self.current_pkg_cursor[INDEX_TYPES[mode]][0]:
                    self.package_view.set_cursor(
                        self.current_pkg_path[INDEX_TYPES[mode]],
                        self.current_pkg_cursor[INDEX_TYPES[mode]][1])
            self.view_filter_changed(self.widget["view_filter"])
            # reset the upgrades list if it is loaded and not being viewed
            self.loaded["Upgradable"] = False
        else:
            if self.reload:
                #debug.dprint("StatusHandler: _update_db_done()... " +
                    #"must be an Upgradable view")
                self.widget['view_refresh'].set_sensitive(True)
                ## hmm, don't mess with upgrade list
                ## after an emerge finishes.
            else:
                debug.dprint("StatusHandler:_update_db_done(); " +
                    "db_thread is done, reload_view()")
                # need to wait until all other events are done for it to
                # show when the window first opens
                gobject.idle_add(self.reload_view)
        debug.dprint("StatusHandler: _update_db_done(); " +
            "Made it thru a reload, returning...")
        self.status.progress_done()
        #if not self.reload:
        #self.view_filter_changed(self.widget["view_filter"])
        self.reload = False
        return False  # disconnect from timeout

    def _reader_done(self, reader_type):
        """perform the cleanup"""
        self.reader.join()
        self.reader_running = False
        self.status.progress_done()
        self.set_cancel_btn(OFF)
        if self.reader.cancelled:
            return False
        debug.dprint("MAINWINDOW: _reader_done(): " +
            "reader_type = " + reader_type)
        if reader_type in ["Upgradable", "Deprecated", "Sets"]:
            self.pkg_list[reader_type] = self.reader.pkg_dict
            self.pkg_count[reader_type] = self.reader.pkg_count
            debug.dprint("MAINWINDOW: _reader_done(): " +
                "pkg_count = " + str(self.pkg_count))
            self.loaded[reader_type] = True
            self.view_filter_changed(self.widget["view_filter"])
            if self.loaded_callback[reader_type]:
                self.loaded_callback[reader_type](None)
                self.loaded_callback[reader_type] = None
            else:
                if self.last_view_setting == SHOW_UPGRADE:
                    self.package_view.set_view(UPGRADABLE)
                    self.packagebook.summary.update_package_info(None)
                elif self.last_view_setting == SHOW_DEPRECATED:
                    self.package_view.set_view(DEPRECATED)
                    self.packagebook.summary.update_package_info(None)
                elif self.last_view_setting == SHOW_SETS:
                    self.package_view.set_view(SETS)
                    self.packagebook.summary.update_package_info(None)
            return False

