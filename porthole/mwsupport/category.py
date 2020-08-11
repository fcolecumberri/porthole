#!/usr/bin/env python

'''
    Porthole Mainwindow Category support
    Support class and functions for the mainwindow interface

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


from porthole import db
from porthole.utils import debug
from porthole.views.category import CategoryView

from porthole.mwsupport.package import PackageHandler
from porthole.mwsupport.constants import (
    INDEX_TYPES,
    SHOW_ALL,
    SHOW_INSTALLED,
    SHOW_SEARCH,
    SHOW_UPGRADE,
    SHOW_DEPRECATED,
    SHOW_SETS
)


class CategoryHandler(PackageHandler):
    '''Support functions for changing categories'''

    def __init__(self):
        '''basic init
        '''
        PackageHandler.__init__(self)
        self.category_view = None
        self.current_cat_name = None
        self.current_cat_cursor = None
        self.current_pkg_cursor = []
        self.current_pkg_name = None
        self.current_pkg_cursor = None
        self.current_pkg_path = None
        self.current_search = None
        self.current_search_cursor = None
        self.pkg_list = None
        # setup the category view
        self.category_view = CategoryView()
        self.category_view.register_callback(self.category_changed)
        self.wtree.get_object("category_scrolled_window"
                        ).add(self.category_view)
        self.plugin_views = None

    def category_changed(self, category):
        """Catch when the user changes categories."""
        mode = self.widget["view_filter"].get_active()
        if mode in list(self.plugin_views.keys()):
            self.plugin_views[mode]["category_changed"](category)
            return
        # log the new category for reloads
        self._remember_selected(mode, category)
        if not self.reload:
            self.current_pkg_cursor["All"] = None
            self.current_pkg_cursor["Installed"] = None
        #debug.dprint("Category cursor = " +
            #str(self.current_cat_cursor["All_Installed"]))
        #debug.dprint("Category = " + category)
        #debug.dprint(self.current_cat_cursor["All_Installed"][0])#[1])
        (cursor, sub_row) = self._get_cursor(mode)
        self.clear_package_detail()
        if not category or sub_row:
            debug.dprint('CategoryHandler: category_changed(); category=False or '+
                'self.current_cat_cursor['+INDEX_TYPES[mode]+'][0][1]==None')
            self.current_pkg_name[INDEX_TYPES[mode]] = None
            self.current_pkg_cursor[INDEX_TYPES[mode]] = None
            self.current_pkg_path[INDEX_TYPES[mode]] = None
            #self.package_view.set_view(PACKAGES)
            self.package_view.populate(None)
        elif mode in [SHOW_UPGRADE, SHOW_DEPRECATED, SHOW_SETS,
                SHOW_SEARCH, SHOW_ALL, SHOW_INSTALLED]:
            # call the correct mode function to handle the change
            getattr(self, '_mode_%s_' %INDEX_TYPES[mode].lower())(category, mode)
        else:
            raise Exception("The programmer is stupid. " +
                "Unknown category_changed() mode")

    def refresh(self):
        """Refresh PackageView"""
        debug.dprint("MAINWINDOW: refresh()")
        mode = self.widget["view_filter"].get_active()
        if mode in [SHOW_SEARCH]:
            self.category_changed(self.current_search)
        else:
            self.category_changed(self.current_cat_name[INDEX_TYPES[mode]])

    def _mode_search_(self, category, mode):
        packages = self.pkg_list["Search"][category]
        # if search was a package name, select that one
        # (searching for 'python' for example would benefit)
        self.package_view.populate(packages, category)

    def _mode_readers_(self, category, mode):
        packages = self.pkg_list[INDEX_TYPES[mode]][category]
        self.package_view.populate(packages,
            self.current_pkg_name[INDEX_TYPES[mode]])

    def _mode_readers_cpv_(self, category, mode):
        packages = self.pkg_list[INDEX_TYPES[mode]][category]
        self.package_view.populate_cpv(packages,
            self.current_pkg_name[INDEX_TYPES[mode]])

    def _mode_all_(self, category, mode):
        packages = db.db.categories[category]
        self.package_view.populate(packages,
            self.current_pkg_name["All"])

    def _mode_installed_(self, category, mode):
        packages = db.db.installed[category]
        self.package_view.populate(packages,
            self.current_pkg_name["Installed"])

    def _mode_upgradable_(self, category, mode):
        self._mode_readers_(category, mode)

    def _mode_deprecated_(self, category, mode):
        if category == "Ebuilds":
            self._mode_readers_cpv_(category, mode)
        else:
            self._mode_readers_(category, mode)

    def _mode_sets_(self, category, mode):
        self._mode_readers_(category, mode)

    def _mode_binpkgs_(self, category, mode):
        packages = db.db.binpkgs[category]
        self.package_view.populate(packages,
            self.current_pkg_name["Binpkgs"])

    def _remember_selected(self, mode, category):
        """Store the selected category and package for the mode"""
        if mode in [SHOW_SEARCH]:
            self.current_search = category
            self.current_search_cursor = self.category_view.get_cursor()
        elif mode not in [SHOW_SEARCH]: #, SHOW_UPGRADE, SHOW_SETS]:
            self.current_cat_name[INDEX_TYPES[mode]] = category
            self.current_cat_cursor[INDEX_TYPES[mode]] = \
                self.category_view.get_cursor()
        #~ elif mode == SHOW_UPGRADE:
            #~ self.current_cat_name["All_Installed"]["Upgradable"] = category
            #~ self.current_upgrade_cursor = self.category_view.get_cursor()

    def _get_cursor(self, mode):
        """returns the previous cursor and subrow
        selections for mode"""
        if self.current_cat_cursor[INDEX_TYPES[mode]]:
            cursor = self.current_cat_cursor[INDEX_TYPES[mode]][0]
            if cursor and len(cursor) > 1:
                sub_row = cursor[1] == None
            else:
                sub_row = False
        else:
            cursor = None
            sub_row = False
        return (cursor, sub_row)

    def select_category_package(self, cat, pack):
        """method to re-select the same category and package that
        were selected last time in this view

        @param cat: category string to re-select
        @param pack package to re-select
        """
        debug.dprint("CategoryHandler: select_category_package(): " +
            "%s/%s" % (cat, pack))
        catpath = None
        if  cat and '-' in cat:
            # find path of category
            catpath = self._find_catpath(cat)
        elif cat:
            model = self.category_view.get_model()
            _iter = model.get_iter_first()
            while _iter:
                if cat == model.get_value(_iter, 0):
                    catpath = model.get_path(_iter)
                    break
                _iter = model.iter_next(_iter)
        #    catpath = 'Sure, why not?'
        else:
            debug.dprint("CategoryHandler: select_category_package(): bad category?")
        if catpath:
            self.category_view.expand_to_path(catpath)
            self.category_view.last_category = None # so it thinks it's changed
            self.category_view.set_cursor(catpath)
            # now reselect whatever package we had selected
            path = self._find_pkgpath(pack)
            if not path:
                debug.dprint("CategoryHandler: select_category_package(): " +
                    "no package found")
                self.clear_package_detail()
        else:
            debug.dprint("CategoryHandler: select_category_package(): " +
                "no category path found")
            self.clear_package_detail()

    def _find_catpath(self, cat):
        """Find the path for the category

        @param cat: category string
        """
        model = self.category_view.get_model()
        _iter = model.get_iter_first()
        catmaj, catmin = cat.split("-", 1)
        debug.dprint("CategoryHandler: _find_catpath(); catmaj, catmin = %s, %s"
            % (catmaj, catmin))
        while _iter:
            debug.dprint("value at iter %s: %s"
                % (iter, model.get_value(_iter, 0)))
            if catmaj == model.get_value(_iter, 0):
                (catpath, kiditer) = self._find_catmin(_iter, catmin, model)
                if catpath:
                    debug.dprint("CategoryHandler: _find_catpath(); " +
                        "found value at iter %s: %s"
                        % (_iter, model.get_value(kiditer, 0)))
                    break
            _iter = model.iter_next(_iter)
        return catpath

    def _find_catmin(self, _iter, catmin, model):
        """Find the minor category belonging to the parent @ _iter"""
        kids = model.iter_n_children(_iter)
        while kids: # this will count backwards, but hey so what
            kiditer = model.iter_nth_child(_iter, kids - 1)
            if catmin == model.get_value(kiditer, 0):
                catpath = model.get_path(kiditer)
                break
            kids -= 1
        return (catpath, kiditer)

