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
import gtk, gobject, pango
import portagelib
import threading
import threading

from depends import DependsTree
from utils import get_treeview_selection, get_icon_for_package, dprint
from portagelib import World
from gettext import gettext as _

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

def PackageModel():
	"""Common model for a package Treestore"""
	return gtk.TreeStore(gobject.TYPE_STRING,
				gobject.TYPE_BOOLEAN,
				gobject.TYPE_PYOBJECT,
				gtk.gdk.Pixbuf,
				gobject.TYPE_BOOLEAN,
				gobject.TYPE_STRING,
				str, str, str, str )
	
class PackageView(CommonTreeView):
    """ Self contained treeview of packages """
    def __init__(self):
        """ Initialize """
        self.new_thread = None
        # initialize the treeview
        CommonTreeView.__init__(self)
        # setup some variables for the different views
        self.PACKAGES = 0
        self.SEARCH_RESULTS = 1
        self.UPGRADABLE = 2

        # setup the treecolumn
        self._column = gtk.TreeViewColumn(_("Packages"))
        self._column.set_resizable(True)
        self.append_column(self._column)

	# Setup the Installed Column
	self._installed_column = gtk.TreeViewColumn(_("Installed"))
	self.append_column( self._installed_column )
	self._installed_column.set_resizable(True)
	self._installed_column.set_expand(False)

	# Setup the Latest Column
	self._latest_column = gtk.TreeViewColumn(_("Latest"))
	self.append_column( self._latest_column )
	self._latest_column.set_resizable(True)
	self._latest_column.set_expand(False)
	
	# setup the packagesize column
	self._size_column = gtk.TreeViewColumn(_("Download Size"))
	self.append_column(self._size_column)
	self._size_column.set_resizable(True)
	self._size_column.set_expand(False)
	
	# setup the Description column
	self._desc_column = gtk.TreeViewColumn(_("Description"))
	self.append_column( self._desc_column )
	self._desc_column.set_resizable( True )
	self._desc_column.set_expand( False )

        # setup the treemodels
        self.upgrade_model = PackageModel()
        self.package_model = PackageModel()
        self.search_model =  PackageModel()
        self.search_model.size = 0
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
        self._size_column.clear()
        self._latest_column.clear()
        self._installed_column.clear()
        self._desc_column.clear()
        if self.current_view == self.UPGRADABLE:
            # add the toggle renderer
            check = gtk.CellRendererToggle()
            self._column.pack_start(check, expand = False)
            self._column.add_attribute(check, "active", 1)
            # add the pixbuf renderer
            pixbuf = gtk.CellRendererPixbuf()
            self._column.pack_start(pixbuf, expand = False)
            self._column.add_attribute(pixbuf, "pixbuf", 3)

        else:
            # add the pixbuf renderer
            pixbuf = gtk.CellRendererPixbuf()
            self._column.pack_start(pixbuf, expand = False)
            self._column.add_attribute(pixbuf, "pixbuf", 3)
        # add the text renderer
        text = gtk.CellRendererText()
        self._column.pack_start(text, expand = True)
        #self._column.add_attribute(text, "text", 0)
        self._column.set_cell_data_func(text, self.render_name, None)
        text_size = gtk.CellRendererText()
        text_installed = gtk.CellRendererText()
        text_latest = gtk.CellRendererText()
        self._size_column.pack_start(text_size, expand = False)
        self._size_column.add_attribute(text_size, "text", 6)
        self._installed_column.pack_start(text_installed, expand = False)
        self._latest_column.pack_start(text_latest, expand = False)
        self._installed_column.add_attribute(text_installed, "text", 7)
        self._latest_column.add_attribute(text_latest, "text", 8)
        self._latest_column.set_sizing( gtk.TREE_VIEW_COLUMN_GROW_ONLY )
        self._installed_column.set_sizing( gtk.TREE_VIEW_COLUMN_GROW_ONLY )
        self._size_column.set_sizing( gtk.TREE_VIEW_COLUMN_GROW_ONLY )
        text_desc = gtk.CellRendererText()
        self._desc_column.pack_start( text_desc, expand=False )
        self._desc_column.add_attribute( text_desc, 'text', 9 )
        self._desc_column.set_sizing( gtk.TREE_VIEW_COLUMN_GROW_ONLY )

        # set the last selected to nothing
        self._last_selected = None

    def render_name(self, column, renderer, model, iter, data):
            """function to render the package name according
               to whether it is in the world file or not"""
            full_name = model.get_value(iter, 0)
            color = model.get_value(iter, 5)
            if model.get_value(iter, 4):
                renderer.set_property("weight", pango.WEIGHT_BOLD)
            else:
                renderer.set_property("weight", pango.WEIGHT_NORMAL)
            if color:
                #if color == 'blue':
                renderer.set_property("foreground", color)
                #else:
                #    renderer.set_property("background", color)
            else:
                renderer.set_property("foreground-set", False)
                #renderer.set_property("background-set", False)
            renderer.set_property("text", full_name)

    def _set_model(self):
        """ Set the correct treemodel for the current view """
        if self.current_view == self.PACKAGES:
            self.set_model(self.package_model)
        elif self.current_view == self.SEARCH_RESULTS:
            self.set_model(self.search_model)
        else:
            self.set_model(self.upgrade_model)

    def register_callbacks(self, package_changed = None, upgrade_selected = None, return_path = None):
        """ Register callbacks for events """
        self._package_changed = package_changed
        self._upgrade_selected = upgrade_selected
        self._return_path = return_path

    def _clicked(self, treeview, *args):
        """ Handles treeview clicks """
        dprint("VIEWS: Package view _clicked() signal caught")
        # get the selection
        package = get_treeview_selection(treeview, 2)
        #dprint("VIEWS: package = ")
        #dprint(package)
        if not package:
            if self._package_changed:
                self._package_changed(None)
            return
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

    def populate(self, packages, locate_name = None):
        """ Populate the current view with packages """
        if not packages:
            return
        dprint("VIEWS: Populating package view")
        dprint("VIEWS: PackageView.populate(); Threading info: %s" %str(threading.enumerate()) )
        #~ if self.new_thread:
            #~ if self.new_thread.isAlive():
                #~ self.new_thread.join()
        if locate_name:
            dprint("VIEWS: Selecting " + str(locate_name))
        # get the right model
        model = self.get_model()
        model.clear()
        names = portagelib.sort(packages.keys())
        for name in names:
            # go through each package
            iter = model.insert_before(None, None)
            model.set_value(iter, 2, packages[name])
            model.set_value(iter, 4, (packages[name].in_world))
            model.set_value(iter, 0, name)
            model.set_value(iter, 5, '') # foreground text color
            # get an icon for the package
            icon = get_icon_for_package(packages[name])
            model.set_value(iter, 3,
                self.render_icon(icon,
                                 size = gtk.ICON_SIZE_MENU,
                                 detail = None))
            if locate_name:
                if name == locate_name:
                    path = model.get_path(iter)
                    if path:
                        # registered callback function to store the path
                        self._return_path(path)
                        #self.set_cursor(path) # does not select it at the
                        # correct place in the code to display properly
                        # get the position in the tree and save it instead
        #~ if self.new_thread:
            #~ if self.new_thread.isAlive():
                #~ self.new_thread.join()
            #~ del self.new_thread
        #~ self.new_thread = threading.Thread( target=self.populate_info )
        #~ self.new_thread.start()

    def populate_info(self):
        """ Populate the current view with packages """
        model = self.get_model()
        iter = model.get_iter_first()
        while iter:
            package = model.get_value( iter, 2)
            package.get_size()
            package.get_latest_installed()
            package.get_latest_ebuild()
            iter = model.iter_next( iter )

        # self._desc_column.set_sizing( gtk.TREE_VIEW_COLUMN_FIXED )
        # self._installed_column.set_sizing( gtk.TREE_VIEW_COLUMN_FIXED )
        # self._latest_column.set_sizing( gtk.TREE_VIEW_COLUMN_FIXED )
        # self._size_column.set_sizing( gtk.TREE_VIEW_COLUMN_FIXED )
        iter = model.get_iter_first()
        while iter:
            package = model.get_value( iter, 2 )
            model.set_value(iter, 6, package.get_size())	    
            try:
                installed = package.get_latest_installed()
                installed = portagelib.get_version( installed )
            except IndexError:
                installed = ""
            try:
                latest = package.get_latest_ebuild()
                latest = portagelib.get_version( latest )
            except IndexError, TypeError:
                latest = "Error"
            model.set_value(iter, 7, installed)
            model.set_value(iter, 8, latest)
            model.set_value(iter, 9, package.get_properties().description )
            iter = model.iter_next( iter )
            # self._desc_column.set_sizing( gtk.TREE_VIEW_COLUMN_AUTOSIZE )
            # self._installed_column.set_sizing( gtk.TREE_VIEW_COLUMN_AUTOSIZE )
            # self._latest_column.set_sizing( gtk.TREE_VIEW_COLUMN_AUTOSIZE )
            # self._size_column.set_sizing( gtk.TREE_VIEW_COLUMN_AUTOSIZE )

            #~ def set_all(self, treeview, selected, checklist):
            #~ """ Sets all (up/down)gradeable packages to value of (selected) accoring to
            #~ the checklist[]""" 
            #~ for len(treeview)
            #~ self.upgrade_model.set_value(iter, 1, selected)

class CategoryView(CommonTreeView):
    """ Self contained treeview to hold categories """
    def __init__(self):
        """ Initialize """
        # initialize the treeview
        CommonTreeView.__init__(self)
        # setup the column
        self.cat_column = gtk.TreeViewColumn(_("Categories"),
                                    gtk.CellRendererText(),
                                    markup = 0)
        self.append_column(self.cat_column)
        # setup the model
        self.model = gtk.TreeStore(gobject.TYPE_STRING,
                                   gobject.TYPE_STRING)
        self.set_model(self.model)
        # connect to clicked event
        self.last_category = None
        self.connect("cursor-changed", self._clicked)
        # register default callback
        self.register_callback()
        self.search_cat = False
        dprint("VIEWS: Category view initialized")

    def set_search( self, option ):
        self.search_cat = option
        if option == True:
            self.cat_column.set_title("Search History")
        elif option == False:
            self.cat_column.set_title("Categories")


    def register_callback(self, category_changed = None):
        """ Register callbacks for events """
        self._category_changed = category_changed

    def _clicked(self, treeview, *args):
        """ Handle treeview clicks """
        category = get_treeview_selection(treeview, 1)
        # has the selection really changed?
        if category != self.last_category:
            dprint("VIEWS: category change detected")
            # then call the callback if it exists!
            if self._category_changed:
                self._category_changed(category)
        # save current selection as last selected
        self.last_category = category
        
    def populate(self, categories):
        """Fill the category tree."""
        self.clear()
        if self.search_cat == True:
            self.populate_search( categories )
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
#	dprint( threading.enumerate() )
#	if self.new_thread:
#	    if self.new_thread.isAlive():
#		self.new_thread.join()
            self.model.set_value(sub_cat_iter, 1, cat)

    def populate_search( self, categories ):
        dprint("VIEWS: populating category view with search history")
        for string in categories:
            iter = self.model.insert_before(None, None)
            self.model.set_value( iter, 0, string )
            self.model.set_value( iter, 1, string )



class DependsView(CommonTreeView):
    """ Store dependency information """
    def __init__(self):
        """ Initialize """
        # initialize the treeview
        CommonTreeView.__init__(self)
        # setup the column
        column = gtk.TreeViewColumn(_("Dependencies"))
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
        return self

    def fill_depends_tree(self, treeview, package):
        """ Fill the dependency tree with dependencies """
        self.model.fill_depends_tree(treeview, package)

    def populate_info(self):
        """ Populate the current view with packages """
        model = self.get_model()
        iter = model.get_iter_first()
        while iter:
            package = model.get_value( iter, 2 )
            model.set_value(iter, 6, package.get_size())	    
            try:
                installed = package.get_latest_installed()
                installed = portagelib.get_version( installed )
            except IndexError:
                installed = ""
            try:
                latest = package.get_latest_ebuild()
                latest = portagelib.get_version( latest )
            except IndexError, TypeError:
                latest = "Error"
            model.set_value(iter, 7, installed)
            model.set_value(iter, 8, latest)
            model.set_value(iter, 9, package.get_properties().description )
            iter = model.iter_next( iter )


