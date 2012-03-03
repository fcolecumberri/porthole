#!/usr/bin/env python

'''
    Porthole Mainwindow Package support class
    Support class and functions for the main interface

    Copyright (C) 2003 - 2011
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

from gettext import gettext as _

from porthole import config
from porthole import db
from porthole.utils import utils, debug
from porthole.readers.search import SearchReader
from porthole.views.packagebook.notebook import PackageNotebook
from porthole.views.package import PackageView
from porthole.views.models import MODEL_ITEM as PACKAGE_MODEL_ITEM
from porthole.dialogs.simple import YesNoDialog
from porthole.mwsupport.base import MainBase
from porthole.mwsupport.constants import (INDEX_TYPES, SHOW_SEARCH,
    SHOW_DEPRECATED, GROUP_SELECTABLE)


class PackageHandler(MainBase):
    '''Support functions for the maindow interface'''

    def __init__(self):
        '''basic init'''
        MainBase.__init__(self)
        self.packagebook = None
        self.current_pkg_name = None
        self.current_pkg_cursor = None
        self.current_pkg_path = None
        self.current_pkgview = None
        self.package_view = PackageView()
        self.search_thread = None
        self.loaded = False
        # setup the package treeview
        #self.package_view.register_callbacks(self.package_changed,
                #None, self.pkg_path_callback)
        #self.package_view.register_callbacks(self.packageview_callback)
        self.package_view.register_callbacks(self.action_callback)
        self.plugin_views = None

    def assign_packagebook(self, wtree,
            callbacks, plugin_package_tabs):
        # create the primary package notebook
        self.packagebook = PackageNotebook(wtree,
                callbacks, plugin_package_tabs)



    def package_changed(self, package):
        """Catch when the user changes packages."""
        debug.dprint("PackageHandler: package_changed()")
        mode = self.widget["view_filter"].get_active()
        if mode in self.plugin_views.keys():
            self.plugin_views[mode]["package_changed"](package)
            return
        if not package or package.full_name == _("None"):
            self.clear_package_detail()
            self.current_pkg_name[INDEX_TYPES[0]] = ''
            self.current_pkg_cursor[INDEX_TYPES[0]] = \
                self.package_view.get_cursor()
            self.current_pkg_path[INDEX_TYPES[0]] = \
                self.current_pkg_cursor[INDEX_TYPES[0]][0]
            return
        # log the new package for db reloads
        self.current_pkg_name[INDEX_TYPES[mode]] = package.get_name()
        self.current_pkg_cursor[INDEX_TYPES[mode]] = \
            self.package_view.get_cursor()
        debug.dprint("PackageHandler: package_changed(); new cursor = " +
            str(self.current_pkg_cursor[INDEX_TYPES[mode]]))
        self.current_pkg_path[INDEX_TYPES[mode]] = \
            self.current_pkg_cursor[INDEX_TYPES[mode]][0]
         #debug.dprint("Package name= " +
            #"%s, cursor = " %str(self.current_pkg_name[INDEX_TYPES[x]]))
        #debug.dprint(self.current_pkg_cursor[INDEX_TYPES[x]])
        # the notebook must be sensitive before anything is displayed
        # in the tabs, especially the deps_view
        self.set_package_actions_sensitive(True, package)
        self.packagebook.set_package(package)


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
            self.loaded["Search"] = True # or else
                #v_f_c() tries to call package_search again
            self.widget["view_filter"].set_active(SHOW_SEARCH)
            if config.Prefs.main.search_desc:
                self.set_statusbar2(_("Searching descriptions for %s")
                    % tmp_search_term)
            else:
                self.set_statusbar2(_("Searching for %s") % tmp_search_term)
            # call the thread
            self.search_thread = SearchReader(db.db.list,
                config.Prefs.main.search_desc, tmp_search_term,
                db.db.descriptions, self.search_dispatcher)
            self.search_thread.start()
        return

    def clear_package_detail(self):
        """tells packagebook to clear itself
        sets the package actions options off"""
        if self.packagebook:
            self.packagebook.clear_notebook()
        self.set_package_actions_sensitive(False)

    def _find_pkgpath(self, pack):
        """"""
        model = self.package_view.get_model()
        _iter = model.get_iter_first()
        path = None
        while _iter and pack:
            #debug.dprint("value at _iter %s: %s"
                #% (_iter, model.get_value(_iter, 0)))
            if model.get_value(_iter, 0).split('/')[-1] == pack:
                path = model.get_path(_iter)
                self.package_view._last_selected = None
                self.package_view.set_cursor(path)
                break
            _iter = model.iter_next(_iter)
        return path

    def set_package_actions_sensitive(self, enabled, package = None):
        """Sets package action buttons/menu items to sensitive or not"""
        #debug.dprint("PackageHandler: set_package_actions_sensitive(%d)" %enabled)
        mode = self.widget["view_filter"].get_active()
        if mode in self.plugin_views.keys():
            self.plugin_views[mode]["set_pkg_actions"](enabled, package)
            return
        self.widget["emerge_package1"].set_sensitive(enabled)
        self.widget["adv_emerge_package1"].set_sensitive(enabled)
        self.widget["unmerge_package1"].set_sensitive(enabled)
        self.widget["btn_emerge"].set_sensitive(enabled)
        self.widget["btn_adv_emerge"].set_sensitive(enabled)
        if not enabled or enabled and package.get_installed():
            #debug.dprint("PackageHandler: set_package_actions_sensitive() " +
                #"setting unmerge to %d" %enabled)
            self.widget["btn_unmerge"].set_sensitive(enabled)
            self.widget["unmerge_package1"].set_sensitive(enabled)
        else:
            #debug.dprint("PackageHandler: set_package_actions_sensitive() " +
                #"setting unmerge to %d" %(not enabled))
            self.widget["btn_unmerge"].set_sensitive(not enabled)

            self.widget["unmerge_package1"].set_sensitive(not enabled)
        self.packagebook.notebook.set_sensitive(enabled)

    def upgrade_packages(self, *widget):
        """Upgrade selected packages that have newer versions available."""
        if self.last_view_setting in GROUP_SELECTABLE:
            if not self.get_selected_list():
                debug.dprint("PackageHandler: upgrade_packages(); " +
                    "No packages were selected")
                return
            debug.dprint("PackageHandler: upgrade_packages(); " +
                "packages were selected")
            if self.last_view_setting == SHOW_DEPRECATED:
                # strip out the version and add the slot

                # then send it
                self.send_pkg_list("emerge --update ")
            else:
                self.send_pkg_list("emerge --update ")
        else:
            debug.dprint("MAIN: Upgrades not loaded; upgrade world?")
            self.upgrades_loaded_dialog = YesNoDialog(_("Upgrade requested"),
                self.mainwindow,
                _("Do you want to upgrade all packages in your world file?"),
                 self.upgrades_loaded_dialog_response)

    def process_selection(self, action):
        if self.is_group_selectable():
            self.get_selected_list()
            self.send_pkg_list(action)
            return True
        return False

    def send_pkg_list(self, action):
        """prepares the action command string for the whole
        self.packages_list and initiates them
         """
        if self.is_root or config.Prefs.emerge.pretend:
            emerge_cmd = action
        elif utils.can_sudo():
            emerge_cmd = 'sudo -p "Password: " %s ' % action
        else: # can't sudo, not root
            # display not root dialog and return.
            self.check_for_root()
            return
        #debug.dprint(self.packages_list)
        #debug.dprint(self.keyorder)
        for key in self.keyorder:
            if not self.packages_list[key].in_world:
                debug.dprint("PackageHandler: upgrade_packages(); " +
                    "dependancy selected: " + key)
                options = config.Prefs.emerge.get_string()
                # handle --unmerge as exact cat/pkg-ver?
                if action in ["emerge --unmerge "]:
                    opts = set(['--pretend', '--depclean']).intesection(
                        set(options.split()))
                    options = ' '.join(opts)
                    #
                    if self.last_view_setting == SHOW_DEPRECATED:
                        # only unmerge exact deprecated version
                        pass

                elif "--oneshot" not in options:
                    options = options + " --oneshot "
                if not self.setup_command(key, emerge_cmd  +
                        options + key[:]): #use the full name
                    return
            elif not self.setup_command(key,
                    emerge_cmd + config.Prefs.emerge.get_string() +
                    ' '+key[:]):
                    #use the full name
                return



    def is_group_selectable(self):
        return self.last_view_setting in GROUP_SELECTABLE

    def get_selected_list(self):
        """creates self.packages_list, self.keyorder"""
        debug.dprint("PackageHandler: get_selected_list()")
        my_type = INDEX_TYPES[self.last_view_setting]
        if self.last_view_setting not in GROUP_SELECTABLE:
            debug.dprint("PackageHandler: get_selected_list() " + my_type +
                " view is not group selectable")
            return False
        # create a list of packages selected
        self.packages_list = {}
        self.keyorder = []
        if self.loaded[my_type]:
            debug.dprint("PackageHandler: get_selected_list() '" +
                my_type + "' loaded")
            self.list_model = self.package_view.view_model[my_type]
            # read the my_type tree into a list of packages
            debug.dprint("PackageHandler: get_selected_list(); " +
                "run list_model.foreach() len = " +
                str(len(self.list_model)))
            debug.dprint("PackageHandler: get_selected_list(); self.list_model = " +
                str(self.list_model))
            self.list_model.foreach(self.tree_node_to_list)
            debug.dprint("PackageHandler: get_selected_list(); " +
                "list_model.foreach() Done")
            debug.dprint("PackageHandler: get_selected_list(); " +
                "len(self.packages_list) = " + str(len(self.packages_list)))
            debug.dprint("PackageHandler: get_selected_list(); self.keyorder) = "+
                str(self.keyorder))
            return len(self.keyorder)>0
        else:
            debug.dprint("PackageHandler: get_selected_list() " + my_type +
                " not loaded")
            return False

    def tree_node_to_list(self, model, path, _iter):
        """callback function from gtk.TreeModel.foreach(),
           used to add packages to the self.packages_list,
           self.keyorder lists"""
        #debug.dprint("PackageHandler; tree_node_to_list(): begin building list")
        if model.get_value(_iter, PACKAGE_MODEL_ITEM["checkbox"]):
            name = model.get_value(_iter, PACKAGE_MODEL_ITEM["name"])
            #debug.dprint("PackageHandler; tree_node_to_list(): name '%s'" % name)
            if self.last_view_setting == SHOW_DEPRECATED and \
                    self.current_cat_name[SHOW_DEPRECATED] == "Ebuilds":
                pkg = model.get_value(_iter, PACKAGE_MODEL_ITEM["package"])
                #ver = model.get_value(_iter, PACKAGE_MODEL_ITEM["installed"])
                cpv = name + ":" #+
                if cpv not in self.keyorder:
                    self.packages_list[cpv] = pkg
                    self.keyorder = [cpv] + self.keyorder
            if name not in self.keyorder \
                    and name != _("Upgradable dependencies:"):
                self.packages_list[name] = model.get_value(_iter,
                    PACKAGE_MODEL_ITEM["package"])
                #model.get_value(_iter, PACKAGE_MODEL_ITEM["world"])
                # model.get_value(_iter, PACKAGE_MODEL_INDEX["package"]), name]
                self.keyorder = [name] + self.keyorder
        #debug.dprint("PackageHandler; tree_node_to_list(): new keyorder list = "+
            #str(self.keyorder))
        return False

    def chg_pkgview(self, view):
        if not self.current_pkgview:
            self.wtree.get_widget("package_scrolled_window"
                        ).add(view)
        elif self.current_pkgview != view:
            self.wtree.get_widget("package_scrolled_window"
                        ).remove(self.current_view)
            self.wtree.get_widget("package_scrolled_window"
                        ).add(view)
        self.current_pkgview = view

    def load_descriptions_list(self):
        pass

    def set_statusbar2(self, to_string):
        pass

