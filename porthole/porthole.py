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


class MainWindow:
    """Main Window class to setup and manage main window interface."""
    
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
        category_column = gtk.TreeViewColumn("Categories",
                                             gtk.CellRendererText(),
                                             markup = 0)
        self.wtree.get_widget("category_view").append_column(category_column)
        #set package treeview header
        package_column = gtk.TreeViewColumn("Packages")
        package_pixbuf = gtk.CellRendererPixbuf()
        package_column.pack_start(package_pixbuf, expand = False)
        package_column.add_attribute(package_pixbuf, "pixbuf", 1)
        package_text = gtk.CellRendererText()
        package_column.pack_start(package_text, expand = True)
        package_column.add_attribute(package_text, "text", 0)
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
        """Update the statusbar without having to use push and pop."""
        statusbar = self.wtree.get_widget("statusbar1")
        statusbar.pop(0)
        statusbar.push(0, string)

    def update_db_read(self):
        """Update the statusbar according to the number of packages read."""
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

    def populate_category_tree(self):
        last_catmaj = None
        categories = self.db.categories.keys()
        categories.sort()
        self.category_model = gtk.TreeStore(gobject.TYPE_STRING,
                                            gobject.TYPE_STRING)
        for cat in categories:
            catmaj, catmin = cat.split("-")
            if catmaj != last_catmaj:
                cat_iter = self.category_model.insert_before(None, None)
                self.category_model.set_value(cat_iter, 0, catmaj)
                self.category_model.set_value(cat_iter, 1, None) # needed?
                last_catmaj = catmaj
            sub_cat_iter = self.category_model.insert_before(cat_iter, None)
            self.category_model.set_value(sub_cat_iter, 0, catmin)
            # store full category name in hidden field
            self.category_model.set_value(sub_cat_iter, 1, cat)
        self.wtree.get_widget("category_view").set_model(self.category_model)

    def populate_package_tree(self, category):
        view = self.wtree.get_widget("package_view")
        self.package_model = gtk.TreeStore(gobject.TYPE_STRING,
                                           gtk.gdk.Pixbuf)
        if not category:
            view.set_model(self.package_model)
            return
        packages = self.db.categories[category]
        names =  portagelib.sort(packages.keys())
        for name in names:
            iter = self.package_model.insert_before(None, None)
            self.package_model.set_value(iter, 0, name)
            self.package_model.set_value(
                iter, 1,
                view.render_icon((packages[name].get_installed()
                                  and gtk.STOCK_YES or gtk.STOCK_NO),
                                 size = gtk.ICON_SIZE_MENU,
                                 detail = None))
        view.set_model(self.package_model)

    def emerge_package(self, widget):
        """Emerge the currently selected package."""
        pass

    def unmerge_package(self, widget):
        """Unmerge the currently selected package."""
        pass

    def sync_tree(self, widget):
        """Sync the portage tree and reload it when done."""
        pass

    def upgrade_packages(self, widget):
        """Upgrade all packages that have newer versions available."""
        pass

    def package_search(self, widget):
        """Search package db with a string and display results."""
        pass

    def help_contents(self, widget):
        """Show the help file contents."""
        pass

    def about(self, widget):
        """Show about dialog."""
        dialog = AboutDialog()

    def category_changed(self, treeview):
        """Catch when the user changes categories."""
        model, iter = treeview.get_selection().get_selected()
        category = None
        if iter:
            category = model.get_value(iter, 1)
        self.populate_package_tree(category)

    def package_changed(self, treewiew):
        """Catch when the user changes packages."""
        pass


class AboutDialog:
    """Class to hold about dialog and functionality."""

    def __init__(self):
        #setup glade
        self.gladefile = "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "about_dialog")
        #register callbacks
        callbacks = {"on_ok_clicked" : self.ok_clicked}
        self.wtree.signal_autoconnect(callbacks)

    def ok_clicked(self, widget):
        """Get rid of the about dialog!"""
        self.wtree.get_widget("about_dialog").destroy()



if __name__ == "__main__":
    #make sure gtk lets threads run
    gtk.threads_init()
    #create the main window
    myapp = MainWindow()
    #start the program loop
    gtk.mainloop()


