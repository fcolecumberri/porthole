#!/usr/bin/env python

'''
    Porthole Views
    The view filter classes

    Copyright (C) 2003 - 2008    Fredrik Arnerup, Daniel G. Taylor, Brian Dolbec,
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
import os
from gettext import gettext as _


from porthole import backends
portage_lib = backends.portage_lib
from porthole.backends import utilities
from porthole import config
from porthole import db
from porthole.views.commontreeview import CommonTreeView
from porthole.utils import utils
from porthole.utils import debug
from porthole.views.helpers import *
from porthole.views.models import PackageModel, MODEL_ITEM

PACKAGES = 0
INSTALLED = 1
SEARCH = 2
UPGRADABLE = 3
DEPRECATED = 4
SETS = 5
BLANK = 6
TEMP = 7
MODEL_NAMES = ["All", "Installed", "Search", "Upgradable", "Deprecated", "Sets", "Blank", "Temp"]
GROUP_SELECTABLE = [UPGRADABLE, DEPRECATED , SETS]

class PackageView(CommonTreeView):
    """ Self contained treeview of packages """
    def __init__(self):
        """ Initialize """
        self.info_thread = None
        self.iter = None
        self.model = None
        self.current_view = None
        # initialize the treeview
        CommonTreeView.__init__(self)

        # create popup menu for rmb-click
        arch = "~" + portage_lib.get_arch()
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
        self._column.set_min_width(10)
        self.append_column(self._column)
        self._column.set_sort_column_id(MODEL_ITEM["name"])
        # add checkbox column
        self._checkbox_column = gtk.TreeViewColumn()
        self._checkbox_column.set_resizable(False)
        self.append_column(self._checkbox_column)
        # Setup the Installed Column
        self._installed_column = gtk.TreeViewColumn(_("Installed"))
        self.append_column(self._installed_column)
        self._installed_column.set_resizable(True)
        self._installed_column.set_min_width(10)
        #self._installed_column.set_expand(False)
        self._installed_column.set_sort_column_id(MODEL_ITEM["installed"])
        # Setup the Latest Column
        self._latest_column = gtk.TreeViewColumn(_("Recommended"))
        self.append_column(self._latest_column)
        self._latest_column.set_resizable(True)
        self._latest_column.set_min_width(10)
        #self._latest_column.set_expand(False)
        self._latest_column.set_sort_column_id(MODEL_ITEM["recommended"])
        # setup the packagesize column
        self._size_column = gtk.TreeViewColumn(_("Download Size"))
        self.append_column(self._size_column)
        self._size_column.set_resizable(True)
        self._size_column.set_min_width(10)
        #self._size_column.set_expand(False)
        self._size_column.set_sort_column_id(MODEL_ITEM["size"])
        # setup the Description column
        self._desc_column = gtk.TreeViewColumn(_("Description"))
        self.append_column(self._desc_column)
        self._desc_column.set_resizable(False)
        self._desc_column.set_min_width(10)
        self._desc_column.set_expand(True)
        
        self.clickable_columns = [
            self._column,
            self._installed_column,
            self._latest_column,
            self._size_column,
        ]
        
        # make it easier to read across columns
        self.set_rules_hint(True)
        
        # setup the treemodels
        self.view_model = {}
        for x in MODEL_NAMES[:-1]:
            debug.dprint("VIEWS: initializing Package view_model: " + x)
            self.view_model[x] = PackageModel()
        self.view_model[MODEL_NAMES[TEMP]] = self.view_model[MODEL_NAMES[PACKAGES]]
        self.view_model[MODEL_NAMES[SEARCH]].size = 0
        self.temp_view = None
        # set the view
        self.set_view(PACKAGES) # default view

        # connect to clicked event
        self.connect("cursor_changed", self._clicked)
        self.connect("button_press_event", self.on_button_press)
        # set default callbacks to nothing
        self.register_callbacks()
        debug.dprint("VIEWS: Package view initialized")

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
        self.model = None
        self.iter = None
        # clear the columns
        self._checkbox_column.clear()
        self._column.clear()
        self._size_column.clear()
        self._latest_column.clear()
        self._installed_column.clear()
        self._desc_column.clear()
        if self.current_view in GROUP_SELECTABLE:
            # add the toggle renderer
            check = gtk.CellRendererToggle()
            self._checkbox_column.pack_start(check, expand = False)
            self._checkbox_column.add_attribute(check, "active", MODEL_ITEM["checkbox"])
            check.connect("toggled",self.on_toggled)
            self._checkbox_column.set_visible(True)
            # add the pixbuf renderer
            pixbuf = gtk.CellRendererPixbuf()
            self._column.pack_start(pixbuf, expand = False)
            self._column.add_attribute(pixbuf, "pixbuf", MODEL_ITEM["icon"])

        else:
            self._checkbox_column.set_visible(False)
            # add the pixbuf renderer
            pixbuf = gtk.CellRendererPixbuf()
            self._column.pack_start(pixbuf, expand = False)
            self._column.add_attribute(pixbuf, "pixbuf", MODEL_ITEM["icon"])
        # add the text renderer
        text = gtk.CellRendererText()
        self._column.pack_start(text, expand = True)
        self._column.add_attribute(text, "text",MODEL_ITEM["name"])
        self._column.set_cell_data_func(text, self.cell_data_func, None)
        text_size = gtk.CellRendererText()
        text_installed = gtk.CellRendererText()
        text_latest = gtk.CellRendererText()
        self._size_column.pack_start(text_size, expand = False)
        self._size_column.add_attribute(text_size, "text", MODEL_ITEM["size"])
        self._size_column.set_cell_data_func(text_size, self.cell_data_func, None)
        self._installed_column.pack_start(text_installed, expand = False)
        self._installed_column.add_attribute(text_installed, "text", MODEL_ITEM["installed"])
        self._installed_column.set_cell_data_func(text_installed, self.cell_data_func, None)
        self._latest_column.pack_start(text_latest, expand = False)
        self._latest_column.add_attribute(text_latest, "text", MODEL_ITEM["recommended"])
        self._latest_column.set_cell_data_func(text_latest, self.cell_data_func, None)
        #self._latest_column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        #self._installed_column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        #self._size_column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        text_desc = gtk.CellRendererText()
        self._desc_column.pack_start(text_desc, expand=False)
        self._desc_column.add_attribute(text_desc, 'text', MODEL_ITEM["description"])
        self._desc_column.set_cell_data_func(text_desc, self.cell_data_func, None)
        #self._desc_column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)

        # set the last selected to nothing
        self._last_selected = None

    def cell_data_func(self, column, renderer, model, iter, data):
            """function to render the package name according
               to whether it is in the world file or not"""
            #full_name = model.get_value(iter,MODEL_ITEM["name"])
            color = model.get_value(iter, MODEL_ITEM["text_colour"])
            if model.get_value(iter, MODEL_ITEM["world"]):
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
            #renderer.set_property("text", full_name)

    def _set_model(self):
        """ Set the correct treemodel for the current view """
        debug.dprint("VIEWS: Package_view._set_model(); changing to '" + MODEL_NAMES[self.current_view] + "' view model")
        self.set_model(self.view_model[MODEL_NAMES[self.current_view]])
        if self.current_view in [PACKAGES, SEARCH]:
            #self.remove_model()
            self.popup_menuitems["deselect_all"].hide()
            self.popup_menuitems["select_all"].hide()
            #self.enable_column_sort()
        else:
            #debug.dprint("VIEWS: Package_view._set_model(); changing to '" + MODEL_NAMES[self.current_view] + "' view")
            self.popup_menuitems["deselect_all"].show()
            self.popup_menuitems["select_all"].show()
            #debug.dprint("VIEWS: _set_model(); disabling column sort")
        self.enable_column_sort() #disable_column_sort()

    def register_callbacks(self, callback = None):
        """ Callback to MainWindow.
        Currently takes an action and possibly one argument and passes it or them
        back to the function specified when MainWindow called register_callbacks.
        Actions can be "emerge", "emerge pretend", "unmerge", "set path",
        "package changed" or "refresh".
        """
        self.mainwindow_callback = callback

    def on_button_press(self, treeview, event):
        debug.dprint("VIEWS: Handling PackageView button press event")
        self.event = event # save the event so we can access it in _clicked()
        if event.type != gtk.gdk.BUTTON_PRESS:
            debug.dprint("VIEWS: Strange event type got passed to on_button_press() callback...")
            debug.dprint("VIEWS: event.type =  %s" %str(event.type))
        if event.button == 3: # secondary mouse button
            self.dopopup = True # indicate that the popup menu should be displayed.
        else:
            self.dopopup = False
        # Test to make sure something was clicked on:
        pathinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
        if pathinfo == None:
            self.dopopup = False
            return True
        else:
            path, col, cellx, celly = pathinfo
            debug.dprint("VIEWS: pathinfo = %s" %str(pathinfo))
            #treeview.set_cursor(path, col, MODEL_ITEM["name"]) # Note: sets off _clicked again
        return False

    def on_toggled(self, widget, path):
        self.toggle = path
        debug.dprint("VIEWS: Toggle activated at path '%s'" % path)
        self.set_cursor(path) # sets off _clicked
        return True

    def add_keyword(self, widget):
        arch = "~" + portage_lib.get_arch()
        name = utils.get_treeview_selection(self, MODEL_ITEM["package"]).full_name
        string = name + " " + arch + "\n"
        debug.dprint("VIEWS: Package view add_keyword(); %s" %string)
        def callback():
            self.mainwindow_callback("refresh", {'caller': 'VIEWS: Package view add_keyword()'})
        db.userconfigs.set_user_config('KEYWORDS', name=name, add=arch, callback=callback)

    def emerge(self, widget, pretend=None, sudo=None):
        emergestring = ['emerge']
        if pretend:
            emergestring.append('pretend')
        if sudo:
            emergestring.append('sudo')
        self.mainwindow_callback(emergestring, {'full_name': self._last_selected, 'caller': 'VIEWS: Package view emerge()'})

    def unmerge(self, widget, sudo=None):
        if sudo:
            self.mainwindow_callback(["unmerge", "sudo"], {'full_name': self._last_selected, 'caller': 'VIEWS: Package view unmerge()'})
        else:
            self.mainwindow_callback(["unmerge"], {'full_name': self._last_selected, 'caller': 'VIEWS: Package view unmerge()'})

    def _clicked(self, treeview, *args):
        """ Handles treeview clicks """
        debug.dprint("VIEWS: Package view _clicked() signal caught")
        # get the selection
        package = utils.get_treeview_selection(treeview, MODEL_ITEM["package"])
        #debug.dprint("VIEWS: package = %s" % package.full_name)
        if (not package and not self.toggle) or package.full_name == _("None"):
            self.mainwindow_callback("package changed", {'package': None, 'caller': 'VIEWS: Package view _clicked()'})
            return False
        if self.toggle != None : # for upgrade view
            iter = self.get_model().get_iter(self.toggle)
            check = self.view_model[MODEL_NAMES[self.current_view]].get_value(iter, MODEL_ITEM["checkbox"])
            check = not check
            self.view_model[MODEL_NAMES[self.current_view]].set_value(iter, MODEL_ITEM["checkbox"], check)
            package.is_checked = check
            #~ if self.view_model[MODEL_NAMES[self.current_view]].get_value(iter, MODEL_ITEM["package"]) == None:
                #~ #debug.dprint("VIEWS: _clicked(): Toggling all upgradable deps")
                #~ # package == None for "Upgradable Dependencies" row
                #~ # so select or deselect all deps
                #~ iter = self.view_model[MODEL_NAMES[self.current_view]].iter_children(iter)
                #~ while iter:
                    #~ self.view_model[MODEL_NAMES[self.current_view]].set_value(iter, MODEL_ITEM["checkbox"], check)
                    #~ iter = self.view_model[MODEL_NAMES[self.current_view]].iter_next(iter)
            self.dopopup = False # don't popup menu if clicked on checkbox
            self.toggle = None
            return True # we've got it sorted
        else:
            self.mainwindow_callback("package changed", {'package': package, 'caller': 'VIEWS: Package view _clicked()'})
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
                if utils.can_gksu() and \
                        (package.get_best_ebuild() != package.get_latest_ebuild()):
                    self.popup_menuitems["add-keyword"].show()
                else:
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
        debug.dprint("VIEWS: Populating package view")
        debug.dprint("VIEWS: PackageView.populate(); process_id = %s" %str(os.getpid()))
        if not packages:
            debug.dprint("VIEWS: clearing package view model")
            self.get_model().clear()
            return
        # ask info_thread to die, if alive
        self.infothread_die = "Please"
        self.model = None
        self.iter = None
        if locate_name:
            debug.dprint("VIEWS: Selecting " + str(locate_name))
        # get the right model
        model = self.get_model()
        if not model:
            debug.dprint("VIEWS: populate(); FAILED TO GET model!!!!!!")
            return
        self.disable_column_sort()
        model.clear()
        names = utilities.sort(packages.keys())
        path = None
        locate_count = 0
        for name in names:
            #debug.dprint("VIEWS: PackageView.populate(); name = %s" %name)
            # go through each package
            iter = model.insert_before(None, None)
            model.set_value(iter,MODEL_ITEM["name"], name)
            upgradable = 0
            if name != _("None"):
                model.set_value(iter, MODEL_ITEM["package"], packages[name])
                model.set_value(iter, MODEL_ITEM["checkbox"], (packages[name].is_checked))
                model.set_value(iter, MODEL_ITEM["world"], (packages[name].in_world))
                upgradable = packages[name].is_dep_upgradable()
                if upgradable == MODEL_ITEM["checkbox"]: # portage wants to upgrade
                    model.set_value(iter, MODEL_ITEM["text_colour"], config.Prefs.views.upgradable_fg)
                elif upgradable == -1: # portage wants to downgrade
                    model.set_value(iter, MODEL_ITEM["text_colour"], config.Prefs.views.downgradable_fg)
                else:
                    model.set_value(iter, MODEL_ITEM["text_colour"], '')
                # get an icon for the package
                icon = utils.get_icon_for_package(packages[name])
                model.set_value(iter, MODEL_ITEM["icon"],
                                self.render_icon(icon,
                                size = gtk.ICON_SIZE_MENU,
                                detail = None))
            if locate_name:
                if name.split('/')[-1] == locate_name:
                    locate_count += 1
                    path = model.get_path(iter)
                    #if path:
                        # use callback function to store the path
                        #self.mainwindow_callback("set path", path)
        if locate_count == 1: # found unique exact result - select it
            self.set_cursor(path)
        debug.dprint("VIEWS: starting info_thread")
        self.infothread_die = False
        self.get_model().set_sort_column_id(MODEL_ITEM["name"], gtk.SORT_ASCENDING)
        #self.disable_column_sort()
        self.model = self.get_model()
        self.iter = model.get_iter_first()
        gobject.idle_add(self.populate_info)
 
    def populate_info(self):
        """ Populate the current view with package info"""
        if self.infothread_die:
            return False # will not be called again
        #gtk.threads_enter()
        #model = self.get_model()
        #iter = model.get_iter_first()
        model = self.model
        iter = self.iter
        #gtk.threads_leave()
        #while iter and not (self.infothread_die):
        if iter and not model.get_value(iter,MODEL_ITEM["name"]) == _("None"):
            try:
                #gtk.threads_enter()
                package = model.get_value(iter, MODEL_ITEM["package"])
                #debug.dprint("VIEWS: populate_info(); getting latest_installed")
                latest_installed = package.get_latest_installed()
                #debug.dprint("VIEWS: populate_info(); latest_installed: %s, getting best_ebuild" %str(latest_installed))
                best_ebuild = package.get_best_dep_ebuild()
                #debug.dprint("VIEWS: populate_info(); best_dep_ebuild: %s, getting latest_ebuild" %str(best_ebuild))
                latest_ebuild = package.get_latest_ebuild(include_masked = False)
                #debug.dprint("VIEWS: populate_info(); latest_ebuild: %s" %str(latest_ebuild))
                try:
                    size = package.get_size()
                    #debug.dprint("VIEWS: populate_info(); size = " + size)
                    model.set_value(iter, MODEL_ITEM["size"], size) # Size
                except:
                    debug.dprint("VIEWS: populate_info(); Had issues getting size for '%s'" % str(package.full_name))
                model.set_value(iter, MODEL_ITEM["installed"], portage_lib.get_version(latest_installed)) # installed
                if best_ebuild:
                    model.set_value(iter, MODEL_ITEM["recommended"], portage_lib.get_version(best_ebuild)) #  recommended by portage
                    #debug.dprint("VIEWS populate_info(): got best ebuild for '%s' = %s" % (package.full_name, best_ebuild))
                elif latest_ebuild:
                    model.set_value(iter, MODEL_ITEM["recommended"], "(" + portage_lib.get_version(latest_ebuild) + ")") # latest
                    #debug.dprint("VIEWS populate_info(): got latest ebuild for '%s' = %s" % (package.full_name, latest_ebuild))
                else:
                    model.set_value(iter, MODEL_ITEM["recommended"], "masked") # hard masked - don't display
                    #debug.dprint("VIEWS populate_info(): got masked ebuild for '%s' = %s" % (package.full_name, "masked"))
                try:
                    model.set_value(iter, MODEL_ITEM["description"], package.get_properties().description) # Description
                except:
                    debug.dprint("VIEWS populate_info(): Failed to get item description for '%s'" % package.full_name)
                self.iter = model.iter_next(iter)
                #gtk.threads_leave()
            except Exception, e:
                debug.dprint("VIEWS: populate_info(): Stopping due to exception '%s'" % e)
                #self.iter = model.iter_next(iter)
                return False # will not be called again
                #gtk.threads_leave()
            return True # will be called again
        #if not self.infothread_die:
        else: # reached last iter
            #gtk.threads_enter()
            self.queue_draw()
            #debug.dprint("VIEWS: populate_info(); enabling column sort")
            self.enable_column_sort()
            debug.dprint("VIEWS: populate_info(); Package info populated")
            return False # will not be called again
            #gtk.threads_leave()

    def deselect_all(self, widget):
        """upgrades view deselect all packages callback"""
        debug.dprint("VIEWS: deselect_all(); right click menu call")
        model = self.get_model()
        model.foreach(self.set_select, False)

    def select_all(self, widget):
        """upgrades view deselect all packages callback"""
        debug.dprint("VIEWS: select_all(); right click menu call")
        model = self.get_model()
        model.foreach(self.set_select, True)

    def set_select(self, model, path, iter, selected):
        if model.get_value(iter,MODEL_ITEM["name"]) != _("None"):
            model.set_value(iter, MODEL_ITEM["checkbox"], selected)
            model.get_value(iter, MODEL_ITEM["package"]).is_checked = selected
    
    def remove_model(self): # used by upgrade reader to speed up adding to the model
        self.view_model["Temp"] = self.get_model()
        self.temp_view = self.current_view
        self.set_model(self.view_model["Blank"])
    
    def restore_model(self):
        if self.temp_view == self.current_view: # otherwise don't worry about it
            self.set_model(self.view_model["Temp"])
    
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
