#!/usr/bin/env python

'''
    Porthole
    A graphical frontend to Portage

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

#store our version here
version = 0.1

import os, string, threading, time #if this fails... lol
try:
    import pygtk
    pygtk.require("2.0") #make sure we have the right version
except ImportError:
    print "Error loading libraries!\nIs pygtk installed?"
try:
    import gtk, gtk.glade, gobject
except ImportError:
    print "Error loading libraries!\nIs GTK+ installed?"
try:
    import portagelib
except ImportError:
    print "Error loading libraries!\nCan't find portagelib!"

#mainwindow class to setup and manage main window interface
class MainWindow:
    def __init__(self):
        #setup glade
        self.gladefile = "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "main_window")
        #register callbacks
        callbacks = {
            "on_main_window_destroy" : gtk.mainquit,
            "on_quit1_activate" : gtk.mainquit,
            "on_emerge_package" : self.emerge_package,
            "on_unmerge_package" : self.unmerge_package,
            "on_sync_tree" : self.sync_tree,
            "on_upgrade_packages" : self.upgrade_packages,
            "on_package_search" : self.package_search,
            "on_search_entry_activate": self.package_search,
            "on_help_contents" : self.help_contents,
            "on_about" : self.about,
            "on_category_view_cursor_changed" : self.category_changed,
            "on_package_view_cursor_changed" : self.package_changed
            }
        self.wtree.signal_autoconnect(callbacks)
        #setup our treemodels
        self.category_model = None
        self.package_model = None
        self.search_results = None
        #declare the database
        self.db = None
        #set category treeview header
        category_column = gtk.TreeViewColumn()
        category_column.set_title("Categories")
        category_renderer = gtk.CellRendererText()
        category_column.pack_start(category_renderer, expand = True)
        category_column.add_attribute(category_renderer, "text", 0)
        self.wtree.get_widget("category_view").append_column(category_column)
        #set package treeview header
        package_column = gtk.TreeViewColumn()
        package_column.set_title("Packages")
        package_pixbuf = gtk.CellRendererPixbuf()
        package_text = gtk.CellRendererText()
        package_column.pack_start(package_pixbuf, expand = False)
        package_column.pack_start(package_text, expand = True)
        self.wtree.get_widget("package_view").append_column(package_column)
        #move horizontal and vertical panes
        self.wtree.get_widget("hpane").set_position(200)
        self.wtree.get_widget("vpane").set_position(250)
        #load the db
        self.db_thread = portagelib.DatabaseReader()
        self.db_thread.start()
        gtk.timeout_add(100, self.update_db_read)
        #set status
        self.set_statusbar("Reading package database: %i packages read"
                           % 0)

    def set_statusbar(self, string):
        statusbar = self.wtree.get_widget("statusbar1")
        statusbar.pop(0)
        statusbar.push(0, string)

    #update the statusbar according to the number of packages read
    def update_db_read(self):
        if not self.db_thread.done:
            self.set_statusbar("Reading package database: %i packages read"
                               % self.db_thread.count)
        else:
            self.db = self.db_thread.get_db()
            self.set_statusbar("Populating tree ...")
            self.db_thread.join()
            self.populate_category_tree()
            self.set_statusbar("Idle")
            self.wtree.get_widget("menubar").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("toolbar").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("view_filter").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("search_entry").set_sensitive(gtk.TRUE)
            self.wtree.get_widget("btn_search").set_sensitive(gtk.TRUE)
            return gtk.FALSE  # disconnect from timeout
        return gtk.TRUE

    #populate the category tree
    def populate_category_tree(self):
        last_cat = "None"
        categories = self.db.categories.keys()
        categories.sort()
        self.category_model = gtk.TreeStore(gobject.TYPE_STRING)
        for cat in categories:
            sub_categories = string.split(cat, "-")
            if sub_categories[0] != last_cat:
                cat_iter = self.category_model.insert_before(None, None)
                self.category_model.set_value(cat_iter, 0, sub_categories[0])
                last_cat = sub_categories[0]
            sub_cat_iter = self.category_model.insert_before(cat_iter, None)
            self.category_model.set_value(sub_cat_iter, 0, sub_categories[1])
        self.wtree.get_widget("category_view").set_model(self.category_model)

    #emerge the currently selected package
    def emerge_package(self, widget):
        pass

    #unmerge the currently selected package
    def unmerge_package(self, widget):
        pass

    #sync the portage tree and reload it when done
    def sync_tree(self, widget):
        pass

    #upgrade all packages that have newer versions available
    def upgrade_packages(self, widget):
        pass

    #search package db with a string and display results
    def package_search(self, widget):
        pass

    #show the help file contents
    def help_contents(self, widget):
        pass

    #show about dialog
    def about(self, widget):
        dialog = AboutDialog()

    #catch when the user changes categories
    def category_changed(self, widget):
        print "boing!"

    #catch when the user changes packages
    def package_changed(self, widget):
        pass

#class to hold about dialog and functionality
class AboutDialog:
    def __init__(self):
        #setup glade
        self.gladefile = "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "about_dialog")
        #register callbacks
        callbacks = {"on_ok_clicked" : self.ok_clicked}
        self.wtree.signal_autoconnect(callbacks)

    #get rid of the about dialog!
    def ok_clicked(self, widget):
        self.wtree.get_widget("about_dialog").destroy()

if __name__ == "__main__":
    #make sure gtk lets threads run
    gtk.threads_init()
    #create the main window
    myapp = MainWindow()
    #start the program loop
    gtk.mainloop()


