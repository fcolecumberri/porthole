#!/usr/bin/env python

'''
    Porthole Views
    The view filter classes

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

import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, gobject
import portagelib

from depends import DependsTree
from utils import get_treeview_selection, get_icon_for_package, dprint

class CommonTreeView(gtk.TreeView):
    """ Common functions used by all views """
    def __init__(self):
        """ Initialize """
        # initialize the treeview
        gtk.TreeView.__init__(self)
        # set last selected
        self._last_selected = None
        # show yourself
        self.show_all()

    def clear(self):
        """ Clear current view """
        # get the treemodel
        model = self.get_model()
        if model:
            # clear it
            model.clear()

class PackageView(CommonTreeView):
    """ Self contained treeview of packages """
    def __init__(self):
        """ Initialize """
        # initialize the treeview
        CommonTreeView.__init__(self)
        # setup some variables for the different views
        self.PACKAGES = 0
        self.SEARCH_RESULTS = 1
        self.UPGRADABLE = 2
        # setup the treecolumn
        self._column = gtk.TreeViewColumn("Packages")
        self.append_column(self._column)
        # setup the treemodels
        self.package_model = gtk.TreeStore(gobject.TYPE_STRING,
                                           gtk.gdk.Pixbuf,
                                           gobject.TYPE_PYOBJECT)
        self.search_model = gtk.TreeStore(gobject.TYPE_STRING,
                                          gtk.gdk.Pixbuf,
                                          gobject.TYPE_PYOBJECT)
        self.search_model.size = 0
        self.upgrade_model = gtk.TreeStore(gobject.TYPE_STRING,
                                           gobject.TYPE_BOOLEAN,
                                           gobject.TYPE_PYOBJECT)
        # set the view
        self.set_view(self.PACKAGES) # default view
        # connect to clicked event
        self.connect("cursor_changed", self._clicked)
        # set default callbacks to nothing
        self.register_callbacks()
        dprint("VIEWS: Package view initialized")

    def set_view(self, view):
        """ Set the current view """
        self.current_view = view
        self._init_view()
        self._set_model()

    def _init_view(self):
        """ Set the treeview column """
        # clear the column
        self._column.clear()
        if self.current_view == self.UPGRADABLE:
            # add the toggle renderer
            check = gtk.CellRendererToggle()
            self._column.pack_start(check, expand = False)
            self._column.add_attribute(check, "active", 1)
        else:
            # add the pixbuf renderer
            pixbuf = gtk.CellRendererPixbuf()
            self._column.pack_start(pixbuf, expand = False)
            self._column.add_attribute(pixbuf, "pixbuf", 1)
        # add the text renderer
        text = gtk.CellRendererText()
        self._column.pack_start(text, expand = True)
        self._column.add_attribute(text, "text", 0)
        # set the last selected to nothing
        self._last_selected = None

    def _set_model(self):
        """ Set the correct treemodel for the current view """
        if self.current_view == self.PACKAGES:
            self.set_model(self.package_model)
        elif self.current_view == self.SEARCH_RESULTS:
            self.set_model(self.search_model)
        else:
            self.set_model(self.upgrade_model)

    def register_callbacks(self, package_changed = None, upgrade_selected = None):
        """ Register callbacks for events """
        self._package_changed = package_changed
        self._upgrade_selected = upgrade_selected

    def _clicked(self, treeview):
        """ Handles treeview clicks """
        dprint("VIEWS: Package view _clicked() signal caught")
        # get the selection
        package = get_treeview_selection(treeview, 2)
        #dprint("VIEWS: package = ")
        #dprint(package)
        if self.current_view == self.UPGRADABLE:
            if package.full_name == self._last_selected:
                model, iter = self.get_selection().get_selected()
                check = self.upgrade_model.get_value(iter, 1)
                self.upgrade_model.set_value(iter, 1, not check)
                if self._upgrade_selected:
                    self._upgrade_selected(package)
            elif self._package_changed:
                self._package_changed(package)
        else:
            #dprint("VIEWS: full_name != _last_package = %d" %(package.full_name != self._last_selected))
            if package.full_name != self._last_selected:
                if self._package_changed:
                    dprint("VIEWS: calling registered package_changed()")
                    self._package_changed(package)
        self._last_selected = package.full_name

    def populate(self, packages):
        """ Populate the current view with packages """
        if not packages:
            return
        dprint("VIEWS: Populating package view")
        # get the right model
        model = self.get_model()
        model.clear()
        names = portagelib.sort(packages.keys())
        for name in names:
            # go through each package
            iter = model.insert_before(None, None)
            model.set_value(iter, 0, name)
            model.set_value(iter, 2, packages[name])
            # get an icon for the package
            icon = get_icon_for_package(packages[name])
            model.set_value(iter, 1,
                self.render_icon(icon,
                                 size = gtk.ICON_SIZE_MENU,
                                 detail = None))

        
class CategoryView(CommonTreeView):
    """ Self contained treeview to hold categories """
    def __init__(self):
        """ Initialize """
        # initialize the treeview
        CommonTreeView.__init__(self)
        # setup the column
        column = gtk.TreeViewColumn("Categories",
                                    gtk.CellRendererText(),
                                    markup = 0)
        self.append_column(column)
        # setup the model
        self.model = gtk.TreeStore(gobject.TYPE_STRING,
                                   gobject.TYPE_STRING)
        self.set_model(self.model)
        # connect to clicked event
        self.connect("cursor-changed", self._clicked)
        # register default callback
        self.register_callback()
        dprint("VIEWS: Category view initialized")

    def register_callback(self, category_changed = None):
        """ Register callbacks for events """
        self._category_changed = category_changed

    def _clicked(self, treeview):
        """ Handle treeview clicks """
        category = get_treeview_selection(treeview, 1)
        # has the selection really changed?
        if category != self._last_selected:
            if self._category_changed:
                # then call the callback if it exists!
                self._category_changed(category)
        # save current selection as last selected
        self._last_selected = category
        
    def populate(self, categories):
        """Fill the category tree."""
        self.clear()
        dprint("VIEWS: Populating category view")
        last_catmaj = None
        categories.sort()
        for cat in categories:
            try: catmaj, catmin = cat.split("-")
            except: continue # quick fix to bug posted on forums
            if catmaj != last_catmaj:
                cat_iter = self.model.insert_before(None, None)
                self.model.set_value(cat_iter, 0, catmaj)
                self.model.set_value(cat_iter, 1, None) # needed?
                last_catmaj = catmaj
            sub_cat_iter = self.model.insert_before(cat_iter, None)
            self.model.set_value(sub_cat_iter, 0, catmin)
            # store full category name in hidden field
            self.model.set_value(sub_cat_iter, 1, cat)

class DependsView(CommonTreeView):
    """ Store dependency information """
    def __init__(self):
        """ Initialize """
        # initialize the treeview
        CommonTreeView.__init__(self)
        # setup the column
        column = gtk.TreeViewColumn("Dependencies")
        pixbuf = gtk.CellRendererPixbuf()
        column.pack_start(pixbuf, expand = False)
        column.add_attribute(pixbuf, "pixbuf", 1)
        text = gtk.CellRendererText()
        column.pack_start(text, expand = True)
        column.add_attribute(text, "text", 0)
        self.append_column(column)
        # setup the model
        self.model = DependsTree()
        dprint("VIEWS: Depends view initialized")

    def fill_depends_tree(self, treeview, package):
        """ Fill the dependency tree with dependencies """
        self.model.fill_depends_tree(treeview, package)

