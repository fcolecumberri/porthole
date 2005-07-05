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
import utils

from depends import DependsTree
from utils import dprint
from portagelib import World
from gettext import gettext as _

from portage_const import USER_CONFIG_PATH

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

def size_sort_func(treemodel, iter1, iter2):
    """Sorts by download size"""
    text1 = treemodel.get_value(iter1, 6)
    text2 = treemodel.get_value(iter2, 6)
    try: size1 = int(text1[:-3].replace(',', ''))
    except:
        try: size2 = int(text2[:-3].replace(',', ''))
        except: return 0
        return 1
    try: size2 = int(text2[:-3].replace(',', ''))
    except: return -1
    if size2 > size1: return 1
    if size2 < size1: return -1
    return 0

def latest_sort_func(treemodel, iter1, iter2):
    """Sorts by the difference between the installed and recommended versions"""
    installed1 = treemodel.get_value(iter1, 7)
    installed2 = treemodel.get_value(iter2, 7)
    latest1 = treemodel.get_value(iter1, 8)
    latest2 = treemodel.get_value(iter2, 8)
    if not installed1 or not latest1:
        if not installed2 or not latest2:
            return 0
        return 1
    if not installed2 or not latest2: return -1
    lsplit1 = latest1.split('.')
    lsplit2 = latest2.split('.')
    isplit1 = installed1.split('.')
    isplit2 = installed2.split('.')
    dlist1 = []
    for x in range(min(len(lsplit1), len(isplit1))):
        try: diff = int(lsplit1[x]) - int(isplit1[x])
        except: break
        dlist1.append(diff)
    dlist2 = []
    for x in range(min(len(lsplit2), len(isplit2))):
        try: diff = int(lsplit2[x]) - int(isplit2[x])
        except: break
        dlist2.append(diff)
    for x in range(max(len(dlist1), len(dlist2))):
        if x == len(dlist1): dlist1.append(0)
        if x == len(dlist2): dlist2.append(0)
        if dlist1[x] > dlist2[x]: return -1
        if dlist1[x] < dlist2[x]: return 1
    return 0

def installed_sort_func(treemodel, iter1, iter2):
    """Currently just puts installed packages at the top,
    with world packages above deps"""
    inst1 = treemodel.get_value(iter1, 7)
    inst2 = treemodel.get_value(iter2, 7)
    if not inst1:
        if not inst2:
            return package_sort_func(treemodel, iter1, iter2)
        return 1
    if not inst2:
        return -1
    if treemodel.get_value(iter1, 4): # True if in world file
        if treemodel.get_value(iter2, 4):
            return package_sort_func(treemodel, iter1, iter2)
        return -1
    if treemodel.get_value(iter2, 4):
        return 1
    return package_sort_func(treemodel, iter1, iter2)

def package_sort_func(treemodel, iter1, iter2):
    """Sorts alphabetically by package name"""
    name1 = treemodel.get_value(iter1, 0)
    name2 = treemodel.get_value(iter2, 0)
    if name1 > name2: return 1
    if name2 > name1: return -1
    return 0

def PackageModel():
    """Common model for a package Treestore"""
    store = gtk.TreeStore(
        gobject.TYPE_STRING,        # 0: package name
        gobject.TYPE_BOOLEAN,       # 1: checkbox value in upgrade view
        gobject.TYPE_PYOBJECT,      # 2: package object
        gtk.gdk.Pixbuf,             # 3: room for various icons
        gobject.TYPE_BOOLEAN,       # 4: true if package is in 'world' file
        gobject.TYPE_STRING,        # 5: foreground text colour
        gobject.TYPE_STRING,        # 6: size
        gobject.TYPE_STRING,        # 7: installed version
        gobject.TYPE_STRING,        # 8: portage recommended version
        gobject.TYPE_STRING,        # 9: description
    )
    store.set_sort_func(6, size_sort_func)
    store.set_sort_func(8, latest_sort_func)
    store.set_sort_func(7, installed_sort_func)
    return store

class PackageView(CommonTreeView):
    """ Self contained treeview of packages """
    def __init__(self):
        """ Initialize """
        self.info_thread = None
        self.current_view = None
        # initialize the treeview
        CommonTreeView.__init__(self)
        # setup some variables for the different views
        self.PACKAGES = 0
        self.SEARCH_RESULTS = 1
        self.UPGRADABLE = 2

        # create popup menu for rmb-click
        arch = "~" + portagelib.get_arch()
        menu = gtk.Menu()
        menuitems = {}
        menuitems["emerge"] = gtk.MenuItem(_("Emerge"))
        menuitems["emerge"].connect("activate", self.emerge)
        menuitems["pretend-emerge"] = gtk.MenuItem(_("Pretend Emerge"))
        menuitems["pretend-emerge"].connect("activate", self.emerge, True, None)
        menuitems["sudo-emerge"] = gtk.MenuItem(_("Sudo Emerge"))
        menuitems["sudo-emerge"].connect("activate", self.emerge, None, True)
        menuitems["unmerge"] = gtk.MenuItem(_("Unmerge"))
        menuitems["unmerge"].connect("activate", self.unmerge)
        menuitems["sudo-unmerge"] = gtk.MenuItem(_("Sudo Unmerge"))
        menuitems["sudo-unmerge"].connect("activate", self.unmerge, True)
        menuitems["add-keyword"] = gtk.MenuItem(_("Append with %s to package.keywords") % arch)
        menuitems["add-keyword"].connect("activate", self.add_keyword)
        menuitems["deselect_all"] = gtk.MenuItem(_("De-Select all"))
        menuitems["deselect_all"].connect("activate", self.deselect_all)
        menuitems["select_all"] = gtk.MenuItem(_("Select all"))
        menuitems["select_all"].connect("activate", self.select_all)
        
        for item in menuitems.values():
            menu.append(item)
            item.show()
        
        self.popup_menu = menu
        self.popup_menuitems = menuitems
        self.dopopup = None
        self.event = None
        self.toggle = None
        
        # setup the treecolumn
        self._column = gtk.TreeViewColumn(_("Packages"))
        self._column.set_resizable(True)
        self.append_column(self._column)
        self._column.set_sort_column_id(0)
        # add checkbox column
        self._checkbox_column = gtk.TreeViewColumn()
        self._checkbox_column.set_resizable(False)
        self.append_column(self._checkbox_column)
        # Setup the Installed Column
        self._installed_column = gtk.TreeViewColumn(_("Installed"))
        self.append_column(self._installed_column)
        self._installed_column.set_resizable(True)
        self._installed_column.set_expand(False)
        self._installed_column.set_sort_column_id(7)
        # Setup the Latest Column
        self._latest_column = gtk.TreeViewColumn(_("Recommended"))
        self.append_column(self._latest_column)
        self._latest_column.set_resizable(True)
        self._latest_column.set_expand(False)
        self._latest_column.set_sort_column_id(8)
        # setup the packagesize column
        self._size_column = gtk.TreeViewColumn(_("Download Size"))
        self.append_column(self._size_column)
        self._size_column.set_resizable(True)
        self._size_column.set_expand(False)
        self._size_column.set_sort_column_id(6)
        # setup the Description column
        self._desc_column = gtk.TreeViewColumn(_("Description"))
        self.append_column(self._desc_column)
        self._desc_column.set_resizable(True)
        self._desc_column.set_expand(False)
        
        self.clickable_columns = [
            self._column,
            self._installed_column,
            self._latest_column,
            self._size_column,
        ]
        
        # setup the treemodels
        self.upgrade_model = PackageModel()
        self.package_model = PackageModel()
        self.search_model =  PackageModel()
        self.search_model.size = 0
        self.blank_model = PackageModel()
        self.temp_model = self.package_model
        self.temp_view = None
        # set the view
        self.set_view(self.PACKAGES) # default view

        # connect to clicked event
        self.connect("cursor_changed", self._clicked)
        self.connect("button_press_event", self.on_button_press)
        # set default callbacks to nothing
        self.register_callbacks()
        dprint("VIEWS: Package view initialized")

    def set_view(self, view):
        """ Set the current view """
        if self.current_view == view:
            return
        self.current_view = view
        self._init_view()
        self._set_model()

    def _init_view(self):
        """ Set the treeview column """
        # stop info_thread if running
        self.infothread_die = "Please"
        if self.info_thread:
            if self.info_thread.isAlive():
                dprint("VIEWS: Waiting for info_thread to die")
                gtk.threads_leave()
                self.info_thread.join()
                #gtk.threads_enter()
                dprint("VIEWS: infothread seems to have finished!")
            self.enable_column_sort()
            del self.info_thread
            self.info_thread = None
        # clear the columns
        self._checkbox_column.clear()
        self._column.clear()
        self._size_column.clear()
        self._latest_column.clear()
        self._installed_column.clear()
        self._desc_column.clear()
        if self.current_view == self.UPGRADABLE:
            # add the toggle renderer
            check = gtk.CellRendererToggle()
            self._checkbox_column.pack_start(check, expand = False)
            self._checkbox_column.add_attribute(check, "active", 1)
            check.connect("toggled",self.on_toggled)
            self._checkbox_column.set_visible(True)
            # add the pixbuf renderer
            pixbuf = gtk.CellRendererPixbuf()
            self._column.pack_start(pixbuf, expand = False)
            self._column.add_attribute(pixbuf, "pixbuf", 3)

        else:
            self._checkbox_column.set_visible(False)
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
        self._latest_column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        self._installed_column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        self._size_column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        text_desc = gtk.CellRendererText()
        self._desc_column.pack_start(text_desc, expand=False)
        self._desc_column.add_attribute(text_desc, 'text', 9)
        self._desc_column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)

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
            self.popup_menuitems["deselect_all"].hide()
            self.popup_menuitems["select_all"].hide()
        elif self.current_view == self.SEARCH_RESULTS:
            self.set_model(self.search_model)
            self.popup_menuitems["deselect_all"].hide()
            self.popup_menuitems["select_all"].hide()
        else:
            dprint("VIEWS: Package_view._set_model(); changing to upgrades view")
            self.set_model(self.upgrade_model)
            self.popup_menuitems["deselect_all"].show()
            self.popup_menuitems["select_all"].show()

    def register_callbacks(self, callback = None):
        """ Callback to MainWindow.
        Currently takes an action and possibly one argument and passes it or them
        back to the function specified when MainWindow called register_callbacks.
        Actions can be "emerge", "emerge pretend", "unmerge", "set path",
        "package changed" or "refresh".
        """
        self.mainwindow_callback = callback

    def on_button_press(self, treeview, event):
        dprint("VIEWS: Handling PackageView button press event")
        self.event = event # save the event so we can access it in _clicked()
        if event.type != gtk.gdk.BUTTON_PRESS:
            dprint("VIEWS: Strange event type got passed to on_button_press() callback...")
            dprint(event.type)
        if event.button == 3: # secondary mouse button
            self.dopopup = True # indicate that the popup menu should be displayed.
        else:
            self.dopopup = False
        # Test to make sure something was clicked on:
        pathinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
        if pathinfo == None:
            self.dopopup = False
        else:
            path, col, cellx, celly = pathinfo
            treeview.set_cursor(path, col, 0) # Note: sets off _clicked again
        return False

    def on_toggled(self, widget, path):
        self.toggle = path
        dprint("VIEWS: Toggle activated at path '%s'" % path)
        return False # will continue to _clicked() event

    def add_keyword(self, widget):
        arch = "~" + portagelib.get_arch()
        name = utils.get_treeview_selection(self, 2).full_name
        string = name + " " + arch + "\n"
        dprint("VIEWS: Package view add_keyword(); %s" %string)
        portagelib.set_user_config('package.keywords', name=name, add=arch)
        package = utils.get_treeview_selection(self,2)
        package.best_ebuild = package.get_latest_ebuild()
        self.mainwindow_callback("refresh")

    def emerge(self, widget, pretend=None, sudo=None):
        emergestring = 'emerge'
        if pretend:
            #self.mainwindow_callback("emerge pretend")
            #return
            emergestring += ' pretend'
        #else:
        #    self.mainwindow_callback("emerge")
        if sudo:
            emergestring += ' sudo'
        self.mainwindow_callback(emergestring)

    def unmerge(self, widget, sudo=None):
        if sudo:
            self.mainwindow_callback("unmerge sudo")
        else:
            self.mainwindow_callback("unmerge")

    def _clicked(self, treeview, *args):
        """ Handles treeview clicks """
        dprint("VIEWS: Package view _clicked() signal caught")
        # get the selection
        package = utils.get_treeview_selection(treeview, 2)
        #dprint("VIEWS: package = %s" % package.full_name)
        if not package and not self.toggle:
            self.mainwindow_callback("package changed", None)
            return False
        if self.toggle != None: # for upgrade view
            iter = self.get_model().get_iter(self.toggle)
            check = self.upgrade_model.get_value(iter, 1)
            check = not check
            self.upgrade_model.set_value(iter, 1, check)
            if self.upgrade_model.get_value(iter, 2) == None:
                dprint("VIEWS: _clicked(): Toggling all upgradable deps")
                # package == None for "Upgradable Dependencies" row
                # so select or deselect all deps
                iter = self.upgrade_model.iter_children(iter)
                while iter:
                    self.upgrade_model.set_value(iter, 1, check)
                    iter = self.upgrade_model.iter_next(iter)
            self.dopopup = False # don't popup menu if clicked on checkbox
            self.toggle = None
            return True # we've got it sorted
        else:
            #dprint("VIEWS: full_name != _last_package = %d" %(package.full_name != self._last_selected))
            #if package.full_name != self._last_selected:
            #    #dprint("VIEWS: passing package changed back to mainwindow")
            #    self.mainwindow_callback("package changed", package)
            self.mainwindow_callback("package changed", package)
        self._last_selected = package.full_name

        #pop up menu if was rmb-click
        if self.dopopup:
            if utils.is_root():
                if package.get_best_ebuild() != package.get_latest_ebuild(): # i.e. no ~arch keyword
                    self.popup_menuitems["add-keyword"].show()
                else: self.popup_menuitems["add-keyword"].hide()
                installed = package.get_installed()
                havebest = False
                if installed:
                    self.popup_menuitems["unmerge"].show()
                    if package.get_best_ebuild() in installed:
                        havebest = True
                else:
                    self.popup_menuitems["unmerge"].hide()
                if havebest:
                    self.popup_menuitems["emerge"].hide()
                    self.popup_menuitems["pretend-emerge"].hide()
                else:
                    self.popup_menuitems["emerge"].show()
                    self.popup_menuitems["pretend-emerge"].show()
                self.popup_menuitems["sudo-emerge"].hide()
                self.popup_menuitems["sudo-unmerge"].hide()
            else:
                self.popup_menuitems["emerge"].hide()
                self.popup_menuitems["unmerge"].hide()
                self.popup_menuitems["add-keyword"].hide()
                installed = package.get_installed()
                havebest = False
                if installed and utils.can_sudo():
                    self.popup_menuitems["sudo-unmerge"].show()
                    if package.get_best_ebuild() in installed:
                        havebest = True
                else:
                    self.popup_menuitems["sudo-unmerge"].hide()
                if havebest:
                    self.popup_menuitems["sudo-emerge"].hide()
                    self.popup_menuitems["pretend-emerge"].hide()
                else:
                    if utils.can_sudo():
                        self.popup_menuitems["sudo-emerge"].show()
                    else:
                        self.popup_menuitems["sudo-emerge"].hide()
                    self.popup_menuitems["pretend-emerge"].show()
            self.popup_menu.popup(None, None, None, self.event.button, self.event.time)
            self.dopopup = False
            self.event = None
            return True
 
    def populate(self, packages, locate_name = None):
        """ Populate the current view with packages """
        if not packages:
            return
        dprint("VIEWS: Populating package view")
        dprint("VIEWS: PackageView.populate(); Threading info: %s" %str(threading.enumerate()) )
        # ask info_thread to die, if alive
        self.infothread_die = "Please"
        if self.info_thread:
            if self.info_thread.isAlive():
                dprint("VIEWS: Waiting for info_thread to die")
                gtk.threads_leave()
                self.info_thread.join()
                #gtk.threads_enter()
                dprint("VIEWS: infothread seems to have finished!")
            self.enable_column_sort()
            del self.info_thread
            self.info_thread = None
        if locate_name:
            dprint("VIEWS: Selecting " + str(locate_name))
        # get the right model
        model = self.get_model()
        model.clear()
        names = portagelib.sort(packages.keys())
        path = None
        for name in names:
            # go through each package
            iter = model.insert_before(None, None)
            model.set_value(iter, 2, packages[name])
            model.set_value(iter, 4, (packages[name].in_world))
            model.set_value(iter, 0, name)
            model.set_value(iter, 5, '') # foreground text color
            # get an icon for the package
            icon = utils.get_icon_for_package(packages[name])
            model.set_value(iter, 3,
                self.render_icon(icon,
                                 size = gtk.ICON_SIZE_MENU,
                                 detail = None))
            if locate_name:
                if name == locate_name:
                    path = model.get_path(iter)
                    #if path:
                        # use callback function to store the path
                        #self.mainwindow_callback("set path", path)
        if path:
            self.set_cursor(path)
        dprint("VIEWS: starting info_thread")
        self.infothread_die = False
        self.get_model().set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.disable_column_sort()
        self.info_thread = threading.Thread(target = self.populate_info)
        self.info_thread.setDaemon(True)
        self.info_thread.start()
 
    def populate_info(self):
        """ Populate the current view with package info"""
        gtk.threads_enter()
        model = self.get_model()
        iter = model.get_iter_first()
        gtk.threads_leave()
        while iter and not (self.infothread_die):
            try:
                gtk.threads_enter()
                package = model.get_value(iter, 2)
                latest_installed = package.get_latest_installed()
                best_ebuild = package.get_best_ebuild()
                latest_ebuild = package.get_latest_ebuild(include_masked = False)
                try:
                    model.set_value(iter, 6, package.get_size()) # Size
                except:
                    dprint("VIEWS: populate_info(); Had issues getting size for '%s'" % str(package.full_name))
                model.set_value(iter, 7, portagelib.get_version(latest_installed)) # installed
                if best_ebuild:
                    model.set_value(iter, 8, portagelib.get_version(best_ebuild)) #  recommended by portage
                elif latest_ebuild:
                    model.set_value(iter, 8, "(" + portagelib.get_version(latest_ebuild) + ")") # latest
                else:
                    model.set_value(iter, 8, "masked") # hard masked - don't display
                try:
                    model.set_value(iter, 9, package.get_properties().description) # Description
                except:
                    dprint("VIEWS populate_info(): Failed to get item description for '%s'" % package.full_name)
                iter = model.iter_next(iter)
                gtk.threads_leave()
            except Exception, e:
                dprint("VIEWS: populate_info(); Thread 'package_info' hit exception '%s'. Skipping..." % str(e))
                iter = model.iter_next(iter)
                gtk.threads_leave()
        if not (self.infothread_die):
            gtk.threads_enter()
            self.queue_draw()
            self.enable_column_sort()
            gtk.threads_leave()
        dprint("VIEWS: populate_info(); Package info populated")

    def deselect_all(self, widget):
        """upgrades view deselect all packages callback"""
        dprint("VIEWS: deselect_all(); right click menu call")
        model = self.get_model()
        model.foreach(self.set_select, False)

    def select_all(self, widget):
        """upgrades view deselect all packages callback"""
        dprint("VIEWS: select_all(); right click menu call")
        model = self.get_model()
        model.foreach(self.set_select, True)

    def set_select(self, model, path, iter, selected):
        model.set_value(iter, 1, selected)
    
    def remove_model(self): # used by upgrade reader to speed up adding to the model
        self.temp_model = self.get_model()
        self.temp_view = self.current_view
        self.set_model(self.blank_model)
    
    def restore_model(self):
        if self.temp_view == self.current_view: # otherwise don't worry about it
            self.set_model(self.temp_model)
    
    def column_clicked(self, column):
        # This seems to be unnecessary - gtk does all the work.
        # It would have been useful if column clicks could be escaped,
        # But gtk seems to just ignore "return True" in this case.
        pass
    
    def disable_column_sort(self):
        for col in self.clickable_columns:
            col.set_clickable(False)
    
    def enable_column_sort(self):
        for col in self.clickable_columns:
            col.set_clickable(True)

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
        #category = utils.get_treeview_selection(treeview, 1)
        model, iter = treeview.get_selection().get_selected()
        if iter: category = model.get_value(iter, 1)
        else: category = self.last_category
        # has the selection really changed?
        if category != self.last_category:
            dprint("VIEWS: category change detected")
            # then call the callback if it exists!
            if self._category_changed:
                self.last_category = category
                self._category_changed(category)
        # save current selection as last selected
        self.last_category = category
        
    def populate(self, categories):
        """Fill the category tree."""
        self.clear()
        dprint("VIEWS: Populating category view")
        last_catmaj = None
        categories.sort()
        if self.search_cat == True:
            self.populate_search(categories)
            return
        for cat in categories:
            try: catmaj, catmin = cat.split("-")
            except:
                dprint(" * VIEWS: CategoryView.populate(): can't split '%s'." % cat)
                continue # quick fix to bug posted on forums
            if catmaj != last_catmaj:
                cat_iter = self.model.insert_before(None, None)
                self.model.set_value(cat_iter, 0, catmaj)
                self.model.set_value(cat_iter, 1, None) # needed?
                last_catmaj = catmaj
            sub_cat_iter = self.model.insert_before(cat_iter, None)
            self.model.set_value(sub_cat_iter, 0, catmin)
            # store full category name in hidden field
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
        # set column title to indicate which ebuild we're using
        title = self.get_column(0).get_title()
        self.get_column(0).set_title(_("Dependencies") + ":  " + str(package.get_default_ebuild()))
        self.model.fill_depends_tree(treeview, package)

    def populate_info(self):
        """ Populate the current view with packages """
        model = self.get_model()
        iter = model.get_iter_first()
        while iter:
            package = model.get_value(iter, 2)
            model.set_value(iter, 6, package.get_size())
            try:
                installed = package.get_latest_installed()
                installed = portagelib.get_version(installed)
            except IndexError:
                installed = ""
            try:
                latest = package.get_latest_ebuild()
                latest = portagelib.get_version(latest)
            except IndexError, TypeError:
                latest = "Error"
            model.set_value(iter, 7, installed)
            model.set_value(iter, 8, latest)
            model.set_value(iter, 9, package.get_properties().description )
            iter = model.iter_next( iter )


