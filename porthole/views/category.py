#!/usr/bin/env python

'''
    Porthole Views
    The view filter classes

    Copyright (C) 2003 - 2009 Fredrik Arnerup, Daniel G. Taylor, Brian Dolbec,
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
from models import C_ITEM, CategoryModel

class CategoryView(CommonTreeView):
    """ Self contained treeview to hold categories """
    def __init__(self):
        """ Initialize """
        # initialize the treeview
        CommonTreeView.__init__(self)
        # setup the column
        self.cat_column = gtk.TreeViewColumn(_("Categories"),
                                    gtk.CellRendererText(),
                                    markup = C_ITEM["short_name"])
        self.append_column(self.cat_column)
        self.cat_column.set_visible(True)
        self.cat_column.set_expand(True)
        self.count_column = gtk.TreeViewColumn(_("# pkgs"),
                                    gtk.CellRendererText(),
                                    markup = C_ITEM["count"])
        self.append_column(self.count_column)
        self.count_column.set_visible(True)
        self.count_column.set_expand(False)
       # setup the model
        self.model = CategoryModel()
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
        if iter: category = model.get_value(iter, C_ITEM["full_name"])
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
        #debug.dprint("VIEWS: Populating category view; categories: " + str(categories))
        last_full_names = []
        if _sort:
            categories.sort()
            #debug.dprint("VIEWS: Sorted categories: " + str(categories))
        if self.search_cat == True:
            self.populate_search(categories, counts)
            return
        #set parent_iter to top level
        parent_iter = [None]
        for cat in categories:
            #debug.dprint(" VIEWS: CategoryView.populate():107 cat: %s" %cat)
            if cat: # != 'virtual':
                cat_split = cat.split("-")
                max_level = len(cat_split)-1
                for i in range(len(cat_split)):
                    #debug.dprint(" VIEWS: CategoryView.populate():112 i = " + str(i) + ' ' + str(range(len(cat_split))))
                    # determine the full_name to this level, default to minimum first part of possible split
                    full_name = '-'.join(cat_split[:i+1] or cat_split[0])
                    if i < max_level:
                        # add parent/subparent row
                        len_full_names = len(last_full_names) 
                        #debug.dprint(" VIEWS: CategoryView.populate():i<max_level 117 i = " +str(i) +" new full_name = " + full_name +' >> ' + str(last_full_names) + str(len_full_names))
                        if len_full_names > i  and last_full_names[i] == full_name:
                            #debug.dprint(" VIEWS: CategoryView.populate():i<max_level 119 matching full_name...continuing")
                            continue # skip to the next level
                        # delete any previous deeper levels
                        if i > 0:
                            #debug.dprint(" VIEWS: CategoryView.populate():i>0:123 new parent/sub-parent... truncating parent_iter and flast_full_names")
                            parent_iter = parent_iter[:i+1]
                            last_full_names = last_full_names[:i]
                            #debug.dprint(" VIEWS: CategoryView.populate():i>0:126 full_name, >> = " + full_name +' >> ' + str(last_full_names[i]))
                        else:
                            #debug.dprint(" VIEWS: CategoryView.populate() i=0:128:resetting parent_iter and last_full_names from: " + str(last_full_names))
                            parent_iter = [None]
                            last_full_names = []
                            #debug.dprint(" VIEWS: CategoryView.populate()i=0:131 reset last_full_names from: " + str(last_full_names))
                        #debug.dprint(" VIEWS: CategoryView.populate(): 132 adding parent/subparent category: " + cat_split[i])
                        last_full_names.append(full_name)
                        #debug.dprint(" VIEWS: CategoryView.populate():134 parent_iter = " +str(parent_iter))
                        parent_iter.append(self.model.insert_before(parent_iter[i], None))
                        #debug.dprint(" VIEWS: CategoryView.populate():136 new parent_iter = " +str(parent_iter))
                        #debug.dprint(" VIEWS: CategoryView.populate(): 137 added parent category, path = " +str(
                        #                                self.model.get_path(parent_iter[i+1])))
                        self.model.set_value(parent_iter[i+1], C_ITEM["short_name"], cat_split[i])
                        self.model.set_value(parent_iter[i+1], C_ITEM["full_name"], None) #last_full_names[i]) # needed?
                        #debug.dprint(" VIEWS: CategoryView.populate(): 141 added parent to last_full_names: " + str(last_full_names))
                        self.model.set_value( parent_iter[i+1], C_ITEM["count"], str(0) )
                    else:   # last one, short_name, i == max_level
                        # child row
                        #debug.dprint(" VIEWS: CategoryView.populate(): i = " + str(i) + " 161 end child row '"+ cat_split[i] + "' for: " + full_name)
                        #debug.dprint(" VIEWS: CategoryView.populate():162 parent_iter = " +str(parent_iter))
                        parent_iter = parent_iter[:i+1]
                        last_full_names.append(full_name)
                        parent_iter.append(self.model.insert_before(parent_iter[i], None))
                        #debug.dprint(" VIEWS: CategoryView.populate():166 added end child category path = " +str(
                        #                               self.model.get_path(parent_iter[i+1])))
                        #debug.dprint(" VIEWS: CategoryView.populate():168 parent_iter = " +str(parent_iter))
                        self.model.set_value(parent_iter[i+1], C_ITEM["short_name"], cat_split[i] )
                        self.model.set_value( parent_iter[i+1], C_ITEM["full_name"], full_name )
                        if counts != None: # and counts[cat] != 0:
                            #debug.dprint("VIEWS: Counts: %s = %s" %(cat, str(counts[cat])))
                            self.model.set_value( parent_iter[i+1], C_ITEM["count"], str(counts[cat]) )
                            path = self.model.get_path( parent_iter[i+1])
                            p = i 
                            while p > 0:
                                path = path[:p]
                                #debug.dprint(" VIEWS: CategoryView.populate(): 178 update parent counts path = "+str(path))
                                iter = self.model.get_iter( path)
                                prev_count = self.model.get_value( iter, C_ITEM["count"] )
                                #debug.dprint(" VIEWS: CategoryView.populate(): 181 p = "+str(p)+" prev_count = "+str(prev_count)+" new count = " + str(counts[cat]) +" new parent total = " +str(counts[cat]+int(prev_count)))
                                self.model.set_value( iter, C_ITEM["count"], str(counts[cat]+ int(prev_count)) )
                                p -= 1


    def populate_search( self, categories, counts ):
        debug.dprint("VIEWS: populating category view with search history")
        for string in categories:
            iter = self.model.insert_before(None, None)
            self.model.set_value( iter, C_ITEM["short_name"], string )
            self.model.set_value( iter, C_ITEM["full_name"], string )
            if counts != None: # and counts[string] != 0:
                #debug.dprint("VIEWS: Counts: %s = %s" %(cat, str(counts[string])))
                self.model.set_value( iter, C_ITEM["count"], str(counts[string]) )
