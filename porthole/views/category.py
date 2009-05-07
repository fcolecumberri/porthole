#!/usr/bin/env python

'''
    Porthole Views
    The view filter classes

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor, Brian Dolbec,
    Brian Bockelman, Tommy Iorns

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
import threading, os
from gettext import gettext as _

from porthole.packagebook.depends import DependsTree
from porthole.views.commontreeview import CommonTreeView
from porthole.utils import debug
from porthole.views.helpers import *

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
        self.cat_column.set_visible(True)
        self.cat_column.set_expand(True)
        self.count_column = gtk.TreeViewColumn(_("# pkgs"),
                                    gtk.CellRendererText(),
                                    markup = 2)
        self.append_column(self.count_column)
        self.count_column.set_visible(True)
        self.count_column.set_expand(False)
       # setup the model
        self.model = gtk.TreeStore(gobject.TYPE_STRING, # 0 partial category name
                                   gobject.TYPE_STRING, # 1 full category name
                                   gobject.TYPE_STRING) # 2 pkg count, use string so it can be blank
        self.set_model(self.model)
        # connect to clicked event
        self.last_category = None
        self.connect("cursor-changed", self._clicked)
        # register default callback
        self.register_callback()
        self.search_cat = False
        debug.dprint("VIEWS: Category view initialized")

    def set_search( self, option ):
        self.search_cat = option
        if option == True:
            self.cat_column.set_title(_("Search History"))
        elif option == False:
            self.cat_column.set_title(_("Categories"))


    def register_callback(self, category_changed = None):
        """ Register callbacks for events """
        self._category_changed = category_changed

    def _clicked(self, treeview, *args):
        """ Handle treeview clicks """
        model, iter = treeview.get_selection().get_selected()
        if iter: category = model.get_value(iter, 1)
        else: category = self.last_category
        # has the selection really changed?
        if category != self.last_category:
            debug.dprint("VIEWS: category change detected")
            # then call the callback if it exists!
            if self._category_changed:
                self.last_category = category
                self._category_changed(category)
        # save current selection as last selected
        self.last_category = category
        
    def populate(self, categories, _sort = True, counts = None):
        """Fill the category tree."""
        self.clear()
        debug.dprint("VIEWS: Populating category view; categories: " + str(categories))
        last_catmaj = None
        last_catmaj_iter = None
        if _sort:
            categories.sort()
        if self.search_cat == True:
            self.populate_search(categories, counts)
            return
        for cat in categories:
            #debug.dprint(" VIEWS: CategoryView.populate(): cat: %s" %cat)
            if cat: # != 'virtual':
                try:
                    catmaj, catmin = cat.split("-",1)
                except:
                    # if cat in ["System", "World", "Dependencies"]:
                    iter = self.model.insert_before(None, None)
                    self.model.set_value( iter, 0, cat )
                    self.model.set_value( iter, 1, cat )
                    if counts != None: # and counts[cat] != 0:
                        #debug.dprint("VIEWS: Counts: %s = %s" %(cat, str(counts[cat])))
                        self.model.set_value( iter, 2, str(counts[cat]) )

                    #else:
                    #    debug.dprint(" * VIEWS: CategoryView.populate(): can't split '%s'." % cat)
                    continue # quick fix to bug posted on forums
                if catmaj and catmaj != last_catmaj:
                    cat_iter = self.model.insert_before(None, None)
                    self.model.set_value(cat_iter, 0, catmaj)
                    self.model.set_value(cat_iter, 1, None) # needed?
                    if counts != None:
                        self.model.set_value( cat_iter, 2, str(counts[cat]) )
                    else:
                        self.model.set_value( cat_iter, 2, str(0) )
                    last_catmaj = catmaj
                elif counts != None: # add the count to the catmaj
                    count = int(self.model.get_value( cat_iter, 2 ))
                    #debug.dprint("VIEWS: catmaj counts: %s" %(str(count)))
                    self.model.set_value( cat_iter, 2, str(count + counts[cat]) )
                sub_cat_iter = self.model.insert_before(cat_iter, None)
                self.model.set_value(sub_cat_iter, 0, catmin)
                # store full category name in hidden field
                self.model.set_value(sub_cat_iter, 1, cat)
                if counts != None: # and counts[cat] != 0:
                    #debug.dprint("VIEWS: Counts: %s = %s" %(cat, str(counts[cat])))
                    self.model.set_value( sub_cat_iter, 2, str(counts[cat]) )

    def populate_search( self, categories, counts ):
        debug.dprint("VIEWS: populating category view with search history")
        for string in categories:
            iter = self.model.insert_before(None, None)
            self.model.set_value( iter, 0, string )
            self.model.set_value( iter, 1, string )
            if counts != None: # and counts[string] != 0:
                #debug.dprint("VIEWS: Counts: %s = %s" %(cat, str(counts[string])))
                self.model.set_value( iter, 2, str(counts[string]) )
