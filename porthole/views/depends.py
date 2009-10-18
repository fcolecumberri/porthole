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

from porthole.utils import utils
from porthole import backends
portage_lib = backends.portage_lib
from porthole.packagebook.depends import DependsTree
from porthole.views.commontreeview import CommonTreeView
from porthole.utils import debug
from porthole.views.helpers import *
from porthole import config
from porthole import db




class DependsView(CommonTreeView):
    """ Store dependency information """
    def __init__(self, get_popup, parent_name, parent_tree, dispatcher):
        """ Initialize """
        # initialize the treeview
        CommonTreeView.__init__(self)
        # save the dependency popup callback
        self.get_popup = get_popup
        # parents name we are building the dependency tree for, and some history
        self.parent_tree = parent_tree
        self.parent_name = parent_name
        self.dispatch = dispatcher
        # setup the model
        self.model = DependsTree()
        # setup the column
        column = gtk.TreeViewColumn(_("Dependencies"))
        pixbuf = gtk.CellRendererPixbuf()
        column.pack_start(pixbuf, expand = False)
        column.add_attribute(pixbuf, "pixbuf", 1)
        text = gtk.CellRendererText()
        column.pack_start(text, expand = True)
        column.add_attribute(text, "text", self.model.column["depend"])
        self.append_column(column)
        # Setup the Package Name Column
        self._name_column = gtk.TreeViewColumn(_("Package"))
        self.append_column(self._name_column)
        text_name = gtk.CellRendererText()
        self._name_column.pack_start(text_name, expand = False)
        self._name_column.add_attribute(text_name, "text", self.model.column["name"])
        #self._name_column.set_cell_data_func(text_name, self.cell_data_func, None)
        self._name_column.set_resizable(True)
        self._name_column.set_min_width(10)
        # Setup the Installed Column
        self._installed_column = gtk.TreeViewColumn(_("Installed"))
        self.append_column(self._installed_column)
        text_installed = gtk.CellRendererText()
        self._installed_column.pack_start(text_installed, expand = False)
        self._installed_column.add_attribute(text_installed, "text", self.model.column["installed"])
        #self._installed_column.set_cell_data_func(text_installed, self.cell_data_func, None)
        self._installed_column.set_resizable(True)
        self._installed_column.set_min_width(10)
        #self._installed_column.set_sort_column_id(self.model.column["installed"])
        # Setup the Latest Column
        self._latest_column = gtk.TreeViewColumn(_("Recommended"))
        self.append_column(self._latest_column)
        text_latest = gtk.CellRendererText()
        self._latest_column.pack_start(text_latest, expand = False)
        self._latest_column.add_attribute(text_latest, "text", self.model.column["latest"])
        #self._latest_column.set_cell_data_func(text_latest, self.cell_data_func, None)
        self._latest_column.set_resizable(True)
        self._latest_column.set_min_width(10)
        #self._latest_column.set_sort_column_id(self.model.column["latest"])
        # Setup the keyword Column
        self._keyword_column = gtk.TreeViewColumn(_("Keywords"))
        self.append_column(self._keyword_column)
        text_keyword = gtk.CellRendererText()
        self._keyword_column.pack_start(text_keyword, expand = False)
        self._keyword_column.add_attribute(text_keyword, "text", self.model.column["keyword"])
        #self._keyword_column.set_cell_data_func(text_keyword, self.cell_data_func, None)
        self._keyword_column.set_resizable(True)
        self._keyword_column.set_min_width(10)
        #self._keyword_column.set_sort_column_id(self.model.column["keyword"])
        # Setup the required USE flags  Column
        self._required_use_column = gtk.TreeViewColumn(_("Required USE"))
        self.append_column(self._required_use_column)
        text_use = gtk.CellRendererText()
        self._required_use_column.pack_start(text_use, expand = False)
        self._required_use_column.add_attribute(text_use, "text", self.model.column["required_use"])
        #self._required_use_column.set_cell_data_func(text_use, self.cell_data_func, None)
        self._required_use_column.set_resizable(True)
        self._required_use_column.set_min_width(12)
        #self._required_use_column.set_sort_column_id(self.model.column["required_use"])

        self._last_selected = None
        self.connect("cursor-changed", self._clicked)
        self.connect("button_press_event", self.on_button_press)
        
        
        
        # create popup menu for rmb-click
        arch = "~" + portage_lib.get_arch()
        menu = gtk.Menu()
        menuitems = {}
        menuitems["emerge --oneshot"] = gtk.MenuItem(_("Emerge"))
        menuitems["emerge --oneshot"].connect("activate", self.emerge)
        menuitems["pretend-emerge"] = gtk.MenuItem(_("Pretend Emerge"))
        menuitems["pretend-emerge"].connect("activate", self.emerge, True, None)
        menuitems["sudo-emerge --oneshot"] = gtk.MenuItem(_("Sudo Emerge"))
        menuitems["sudo-emerge --oneshot"].connect("activate", self.emerge, None, True)
        menuitems["Advanced emerge dialog"] = gtk.MenuItem(_("Advanced Emerge"))
        menuitems["Advanced emerge dialog"].connect("activate", self.adv_emerge)
        #menuitems["unmerge"] = gtk.MenuItem(_("Unmerge"))
        #menuitems["unmerge"].connect("activate", self.unmerge)
        #menuitems["sudo-unmerge"] = gtk.MenuItem(_("Sudo Unmerge"))
        #menuitems["sudo-unmerge"].connect("activate", self.unmerge, True)
        menuitems["add-keyword"] = gtk.MenuItem(_("Append with %s to package.keywords") % arch)
        menuitems["add-keyword"].connect("activate", self.add_keyword)
        #menuitems["deselect_all"] = gtk.MenuItem(_("De-Select all"))
        #menuitems["deselect_all"].connect("activate", self.deselect_all)
        #menuitems["select_all"] = gtk.MenuItem(_("Select all"))
        #menuitems["select_all"].connect("activate", self.select_all)
        
        for item in menuitems.values():
            menu.append(item)
            item.show()
        
        self.popup_menu = menu
        self.popup_menuitems = menuitems
        self.dopopup = None
        self.event = None
        self.event_src = None
        self.toggle = None
        self._depend_changed = None
        self.dep_window = {"window": None, "notebook": None, 'tree': []} #, 'depth': 0}
        debug.dprint("DependsView: Depends view initialized")
        #return self

    def fill_depends_tree(self, treeview, package, ebuild):
        """ Fill the dependency tree with dependencies """
        self.parent_name = ebuild
        # set column title to indicate which ebuild we're using
        debug.dprint("DependsView: DependsView.fill_depends_tree(); ebuild = " + ebuild)
        #title = self.get_column(0).get_title()
        self.get_column(0).set_title(_("Dependencies") + ":  " + str(ebuild)) #package.get_default_ebuild()))
        self.model.fill_depends_tree(treeview, package, ebuild)
        self.model.foreach(self.populate_info)

    def populate_info(self, model, path, iter):
        """ Populate the current view with packages """
        #debug.dprint("DependsView: DependsView.populate_info()")
        if model.get_value(iter, model.column["depend"]): # == "None":
                #debug.dprint("DependsView: populate_info(); dependency name = " + model.get_value(iter, model.column["depend"]))
                try:
                    package = model.get_value(iter, model.column["package"])
                    name = package.full_name
                    latest_installed = package.get_latest_installed()
                    #debug.dprint("DependsView: populate_info(); latest_installed: %s, getting best_ebuild" %str(latest_installed))
                    best_ebuild, keyworded_ebuild, masked_ebuild = portage_lib.get_dep_ebuild(model.get_value(iter,model.column["depend"]))
                    #debug.dprint("DependsView: populate_info(); best_ebuild: %s, getting latest_ebuild" %str(best_ebuild))
                    #latest_ebuild = package.get_latest_ebuild(False) # include_masked = False
                    #debug.dprint("DependsView: populate_info(); latest_ebuild: %s" %str(latest_ebuild))
                    model.set_value(iter, model.column["installed"], portage_lib.get_version(latest_installed)) # installed
                    #debug.dprint("DependsView: populate_info(); model.latest_installed version = " + model.get_value(iter, model.column["installed"]))
                    keywords = ''
                    if best_ebuild != '':
                        model.set_value(iter, model.column["latest"], portage_lib.get_version(best_ebuild)) #  recommended by portage
                        name = portage_lib.get_full_name(best_ebuild)
                        keywords = self.get_relevant_keywords(package, best_ebuild)
                    elif keyworded_ebuild != '':
                        model.set_value(iter, model.column["latest"], "(" + portage_lib.get_version(keyworded_ebuild) + ")") # latest
                        name = portage_lib.get_full_name(keyworded_ebuild)
                        keywords = self.get_relevant_keywords(package, keyworded_ebuild)
                    elif masked_ebuild != '':
                        model.set_value(iter, model.column["latest"], "M(" + portage_lib.get_version(masked_ebuild) + ")") # hard masked
                        name = portage_lib.get_full_name(masked_ebuild)
                        keywords = self.get_relevant_keywords(package, masked_ebuild)
                    if latest_installed:
                        name = portage_lib.get_full_name(latest_installed)
                    if "virtual" in name:
                        name = portage_lib.get_virtual_dep(name)
                    model.set_value(iter, model.column["name"], name)
                    model.set_value(iter, model.column["keyword"], keywords)
                except Exception, e:
                    if "'NoneType' object has no attribute " not in str(e):
                        debug.dprint("DependsView: populate_info(): Stopping due to exception %s" % e)
        return False

    def get_relevant_keywords(self, package, ebuild):
        #debug.dprint("DependsView: get_relevant_keywords(); ebuild = " + ebuild)
        keys = package.get_properties(ebuild).get_keywords()
        #debug.dprint("DependsView: get_relevant_keywords(); keys = " + str(keys))
        if config.Prefs.globals.enable_archlist:
            archlist = config.Prefs.globals.archlist
        else:
            archlist = [portage_lib.get_arch()]
        #debug.dprint("DependsView: get_relevant_keywords(); archlist = " + str(archlist))
        keywords = ''
        x = 1
        for arch in archlist:
            if ("~" + arch) in keys:
                if x > 1:
                    keywords = keywords + ", "
                keywords = keywords + "~" + arch
                x += 1
            elif arch in keys:
                if x > 1:
                    keywords = keywords + ", "
                keywords = keywords + arch
                x += 1
        #debug.dprint("DependsView: get_relevant_keywords(); retuning keywords: " + keywords)
        return keywords

    def get_selected(self):
        """get the selected treeview package and name"""
        debug.dprint("DependsView: get_selected()")
        model, iter = self.get_selection().get_selected()
        if iter:
            name = model.get_value(iter, model.column["name"])
            package =  model.get_value(iter, model.column["package"])
            return name, package
        else:
            return self._last_selected, None

    def _clicked(self, treeview, *args):
        """ Handle treeview clicks """
        name, package = self.get_selected()
        # has the selection really changed?
        if name != self._last_selected:
            debug.dprint("DependsView: dependency change detected")
            # then call the callback if it exists!
            if self._depend_changed:
                self._last_selected = name
                self._depend_changed(package)
        # save current selection as last selected
        self._last_selected = name
        
        #pop up menu if was rmb-click and have a valid package
        if self.dopopup and package:
            if utils.is_root():
                if package.get_best_ebuild() != package.get_latest_ebuild(): # i.e. no ~arch keyword
                    self.popup_menuitems["add-keyword"].show()
                else: self.popup_menuitems["add-keyword"].hide()
                installed = package.get_installed()
                havebest = False
                if installed:
                    #self.popup_menuitems["unmerge"].show()
                    if package.get_best_ebuild() in installed:
                        havebest = True
                else:
                    pass
                    #self.popup_menuitems["unmerge"].hide()
                if havebest:
                    self.popup_menuitems["emerge --oneshot"].hide()
                    self.popup_menuitems["pretend-emerge"].hide()
                else:
                    self.popup_menuitems["emerge --oneshot"].show()
                    self.popup_menuitems["pretend-emerge"].show()
                self.popup_menuitems["sudo-emerge --oneshot"].hide()
                #self.popup_menuitems["sudo-unmerge"].hide()
            else:
                self.popup_menuitems["emerge --oneshot"].hide()
                #self.popup_menuitems["unmerge"].hide()
                if utils.can_gksu() and \
                        (package.get_best_ebuild() != package.get_latest_ebuild()):
                    self.popup_menuitems["add-keyword"].show()
                else:
                    self.popup_menuitems["add-keyword"].hide()
                installed = package.get_installed()
                havebest = False
                if installed and utils.can_sudo():
                    #self.popup_menuitems["sudo-unmerge"].show()
                    if package.get_best_ebuild() in installed:
                        havebest = True
                else:
                    pass
                    #self.popup_menuitems["sudo-unmerge"].hide()
                if havebest:
                    self.popup_menuitems["sudo-emerge --oneshot"].hide()
                    self.popup_menuitems["pretend-emerge"].hide()
                else:
                    if utils.can_sudo():
                        self.popup_menuitems["sudo-emerge --oneshot"].show()
                    else:
                        self.popup_menuitems["sudo-emerge --oneshot"].hide()
                    self.popup_menuitems["pretend-emerge"].show()
            self.popup_menu.popup(None, None, None, self.event.button, self.event.time)
            self.dopopup = False
            self.event = None
            return True
 
    def on_button_press(self, widget, event):
        """Catch button events.  When a dbl-click occurs save the widget
            as the source.  When a corresponding button release from the same
            widget occurs, open or change a dep_window to the package details for
            the dependency dbl-clicked on.
        """
        debug.dprint("DependsView: Handling PackageView button press event")
        _do_dep_window = False
        self.event = event # save the event so we can access it in _clicked()
        
        if event.button == 3: # secondary mouse button
            self.dopopup = True # indicate that the popup menu should be displayed.
        else:
            self.dopopup = False
            
        if event.type == gtk.gdk._2BUTTON_PRESS:
            #debug.dprint("DependsView: dbl-click event detected")
            # Capture the source of the dbl-click event
            # but do nothing else
            self.event_src = widget
            debug.dprint("DependsView: button release dbl-click event detected, enabling dep popup")
            _do_dep_window = True

        elif event.type != gtk.gdk.BUTTON_PRESS:
            debug.dprint("DependsView: Strange event type got passed to on_button_press() callback...")
            debug.dprint("DependsView: event.type =  %s" %str(event.type))
            
        elif event.type == gtk.gdk.BUTTON_RELEASE and \
            self.event_src == widget:
            # clear the event source to prevent false restarts
            self.event_src = None
            # The button release event following the dbl-click
            # from the same widget, go ahead and process now
            #debug.dprint("DependsView: button release dbl-click event detected, enabling dep popup")
            _do_dep_window = True
            
        # Test to make sure something was clicked on:
        pathinfo = widget.get_path_at_pos(int(event.x), int(event.y))
        if pathinfo == None:
            debug.dprint("DependsView: pathinfo = None" )
            self.dopopup = do_dep_window = False
            return True
        else:
            #path, col, cellx, celly = pathinfo
            #debug.dprint("DependsView: pathinfo = %s" %str(pathinfo))
            #treeview.set_cursor(path, col, 0) # Note: sets off _clicked again
            name, package = self.get_selected()
            if _do_dep_window and package != None:
                self.do_dep_window(widget)
        return False

    def do_dep_window(self, treeview):
        """ Creates a new window for dependency detail display and sets the package
            or changes the package if there already is an open dep_window.
        """
        debug.dprint("DependsView: do_dep_window(); doing the dep pupoup")
        if self.dep_window["window"] == None or self.dep_window["notebook"] == None:
            #debug.dprint("********** DependsView: do_dep_window(); parent_tree length " + str(len(self.parent_tree)))
            self.parent_tree.append(self.parent_name)
            #debug.dprint("********** DependsView: do_dep_window(); new parent_tree tree & depth " + str(self.parent_tree) + '  ' + str(len(self.parent_tree)))
            self.dep_window = self.get_popup(self.dep_window_callback, self.parent_name, self.parent_tree[:])
        if  self.dep_window["window"] == None or self.dep_window["notebook"] == None:
            #debug.dprint("DependsView: Failed to get the dep_window and/or the dep_notebook")
            return
        self.dep_window["window"].set_title(_("Porthole Dependency Viewer")) 
        self.parent_tree = self.dep_window['tree']
        #debug.dprint("********** DependsView: do_dep_window(); parent_tree dep_window tree length " + str(len(self.parent_tree)) + '  ' + str(len(self.dep_window['tree'])))
        #debug.dprint("********** DependsView: do_dep_window(); new dep_window tree & depth " + str(self.parent_tree) + '  ' + str(len(self.parent_tree)))
        self.dep_window['label'].set_text(self.parent_name)
        self.set_tip_tree()
        # get the package for the popup
        model, iter = treeview.get_selection().get_selected()
        if iter:
            package =  model.get_value(iter, model.column["package"])
        if package:
            #debug.dprint("DependsView: do_dep_window() valid package : " + package.full_name)
            self.dep_window["notebook"].set_package(package)
            self.dep_window["notebook"].notebook.set_sensitive(True)
            # raise window to top of window stack, unminimize, etc.
            self.dep_window["window"].present()
        else:
            #debug.dprint("DependsView: do_dep_window() not a valid package, clearing ")
            self.dep_window["notebook"].clear_notebook()
            self.dep_window["notebook"].notebook.set_sensitive(False)
        #self._depend_changed = self.dep_window["notebook"].set_package

    def set_tip_tree(self):
        #debug.dprint("********** DependsView: set_tip_tree()")
        tip = self.parent_tree[0]
        x = 1
        while x < len(self.parent_tree):
            tip = tip +'\n' + ('    ' *  x) + '|__' + self.parent_tree[x]
            #debug.dprint("********** DependsView: set_tip_tree(); x = " + str(x))
            x += 1
        self.dep_window['label'].set_tooltip_text(tip)
        return

    def set_label(self, name):
        self.parent_name = name
        self.dep_window['label'].set_text(self.parent_name)

    def dep_window_callback(self):
        del self.dep_window["window"], self.dep_window["notebook"]
        self.dep_window["window"] = self.dep_window["notebook"] = None
        #debug.dprint("********** DependsView: dep_window_callback(); deleting last entry in dep_window['tree'] = " + str(self.dep_window['tree'][-1]))
        self.dep_window["tree"] = self.dep_window["tree"][:-1]
        self.parent_tree = self.parent_tree[:-1]
        #debug.dprint("********** DependsView: dep_window_callback(); DependsView: dep_window['tree'] = " + str(self.dep_window['tree']))

    def emerge(self, menuitem_widget, pretend=None, sudo=None):
        emergestring = ['emerge']
        if pretend:
            emergestring.append('pretend')
        if sudo:
            emergestring.append('sudo')
        self.dispatch(emergestring, {'caller': "DependsView: emerge()", 'package': utils.get_treeview_selection(self, 2)})

    def add_keyword(self, widget):
        arch = "~" + portage_lib.get_arch()
        name = utils.get_treeview_selection(self, 2).full_name
        string = name + " " + arch + "\n"
        debug.dprint("DependsView: dependsview add_keyword(); %s" %string)
        db.userconfigs.set_user_config('KEYWORDS', name=name, add=arch, callback=None)

    def adv_emerge(self, widget):
        self.dispatch(["adv_emerge"], {'caller': "DependsView: emerge()", 'package': utils.get_treeview_selection(self, 2)})


