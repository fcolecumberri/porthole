#!/usr/bin/env python

'''
    Porthole Views
    The view filter classes

    Copyright (C) 2003 Fredrik Arnerup and Daniel G. Taylor

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

from utils import get_treeview_selection, get_icon_for_package

class PackageView(gtk.TreeView):
    """ Self contained treeview of packages """
    def __init__(self):
        # initialize the treeview
        gtk.TreeView.__init__(self)
        # setup some variables for the different views
        self.PACKAGES = 0
        self.SEARCH_RESULTS = 1
        self.UPGRADABLE = 2
        #setup the treecolumn
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
        #set the view
        self.set_view(self.PACKAGES) # default view
        # connect to clicked event
        self.connect("cursor_changed", self._clicked)
        # store last selected value
        self._last_selected = None
        # set default callbacks to nothing
        self.register_callbacks()
        # show
        self.show_all()

    def set_view(self, view):
        """ Set the current view """
        self.current_view = view
        self._init_view()
        self._set_model()

    def _init_view(self):
        # clear the column
        self._column.clear()
        if self.current_view == self.UPGRADABLE:
            #add the toggle renderer
            check = gtk.CellRendererToggle()
            self._column.pack_start(check, expand = False)
            self._column.add_attribute(check, "active", 3)
        else:
            #add the pixbuf renderer
            pixbuf = gtk.CellRendererPixbuf()
            self._column.pack_start(pixbuf, expand = False)
            self._column.add_attribute(pixbuf, "pixbuf", 1)
        #add the text renderer
        text = gtk.CellRendererText()
        self._column.pack_start(text, expand = True)
        self._column.add_attribute(text, "text", 0)

    def _set_model(self):
        # Set the correct treemodel for the current view
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
        #get the selection
        package = get_treeview_selection(treeview, 2)
        if self.current_view == self.UPGRADABLE:
            if package == self._last_selected:
                if self._upgrade_selected:
                    check = get_treeview_selection(treeview, 1)
                    print check
                    self._upgrade_selected(package)
            elif self._package_changed:
                self.package_changed(package)
        else:
            if package != self._last_selected:
                if self._package_changed:
                    self._package_changed(package)
        self._last_selected = package

    def populate(self, packages):
        """ Populate the current view with packages """
        if not packages:
            return
        #get the right model
        model = self.get_model()
        model.clear()
        names = portagelib.sort(packages.keys())
        for name in names:
            #go through each package
            iter = model.insert_before(None, None)
            model.set_value(iter, 0, name)
            model.set_value(iter, 2, packages[name])
            #get an icon for the package
            icon = get_icon_for_package(packages[name])
            model.set_value(iter, 1,
                self.render_icon(icon,
                                 size = gtk.ICON_SIZE_MENU,
                                 detail = None))

    def clear(self):
        """ Clear current view """
        model = self.get_model()
        model.clear()
        
