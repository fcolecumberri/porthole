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
    import gtk, gtk.glade, gobject, pango
except ImportError:
    print "Error loading libraries!\nIs GTK+ installed?"
try:
    import portagelib
except ImportError:
    print "Error loading libraries!\nCan't find portagelib!"
try:
    import process
except ImportError:
    print "Error loading libraries!\nCan't find process!"

def xml_esc(string):
    """Escape characters that have special meanings in XML"""
    def subst(c):
        if c == '<': return '&lt;'
        elif c == '>': return '&gt;'
        elif c == '&': return '&amp;'
        else: return c
    return ''.join(map(subst, string))

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
        #setup some textbuffers
        tagtable = self.create_tag_table()
        self.summary_buffer = gtk.TextBuffer(tagtable)
        self.wtree.get_widget("summary_text").set_buffer(self.summary_buffer)
        self.depend_buffer = gtk.TextBuffer(tagtable)
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

    def create_tag_table(self):
        """Define all markup tags."""
        def create(descs):
            table = gtk.TextTagTable()
            for name, properties in descs.items():
                tag = gtk.TextTag(name); table.add(tag)
                for property, value in properties.items():
                    tag.set_property(property, value)
            return table
        return create(
            {'name': ({'weight': pango.WEIGHT_BOLD,
                       'scale': pango.SCALE_X_LARGE}),
             'description': ({"style": pango.STYLE_ITALIC}),
             'url': ({'foreground': 'blue'}),
             'property': ({'weight': pango.WEIGHT_BOLD}),
             'value': ({})
             })

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
        '''fill the category tree'''
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
        '''fill the package tree'''
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
        sync_process = process.ProcessWindow("emerge sync")

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

    def get_treeview_selection(self, treeview, num):
        """Get the value of whatever is selected in a treeview, num is the column"""
        model, iter = treeview.get_selection().get_selected()
        selection = None
        if iter:
            selection = model.get_value(iter, num)
        return selection

    def category_changed(self, treeview):
        """Catch when the user changes categories."""
        category = self.get_treeview_selection(treeview, 1)
        self.populate_package_tree(category)
        self.update_package_info(None)

    def package_changed(self, treeview):
        """Catch when the user changes packages."""
        category = self.get_treeview_selection(
            self.wtree.get_widget("category_view"), 1)
        package = self.get_treeview_selection(treeview, 0)
        self.update_package_info(category + "/" + package)

    def update_package_info(self, package_name):
        """Update the notebook of information about a selected package"""

        def append(text, tag = None):
            """Append text to summary buffer."""
            iter = self.summary_buffer.get_end_iter()
            text_u = text.decode('ascii', 'replace')
            buffer = self.summary_buffer
            if tag:
                buffer.insert_with_tags_by_name(iter, text_u, tag)
            else:
                buffer.insert(iter, text_u)

        def nl():
            append("\n");

        self.summary_buffer.set_text("", 0)
        notebook = self.wtree.get_widget("notebook")
        notebook.set_sensitive(package_name and gtk.TRUE or gtk.FALSE)
        if not package_name:
            #it's really a category selected!
            return
        #put the info into the textview!
        notebook.set_sensitive(gtk.TRUE)
        #set the package
        package = portagelib.Package(package_name)
        package.read_description()
        package.read_versions()
        #read it's info
        description = package.description
        ebuild = package.get_latest_ebuild()
        installed = package.get_installed()
        versions = package.versions
        homepage = package.get_homepage()
        use_flags = package.get_use_flags()
        license = package.get_license()
        slot = package.get_slot()
        #build the information together into a buffer
        ''' TODO:
            get dependencies and show them in the dependency tab/textview
            figure out what to put into the extras tab...?
        '''
        append(package_name, "name"); nl()
        if description:
            append(description, "description"); nl()
        if homepage:
            append(homepage, "url"); nl()
        #put a space between this info and the rest
        nl()
        if installed:
            append("Installed versions: ", "property")
            append(", ".join([portagelib.get_version(ebuild)
                              for ebuild in installed]),
                   "value")
        else:
            append("Not installed", "property")
        nl()
        if versions:
            append("Available versions: ", "property")
            append(", ".join([portagelib.get_version(ebuild)
                              for ebuild in versions]),
                   "value")
        nl()
        #put a space between this info and the rest, again
        nl()
        if use_flags:
            append("Use Flags: ", "property")
            append(", ".join(use_flags), "value")
            nl()
        if license:
            append("License: ", "property");
            append(license, "value");
            nl()
        if slot:
            append("Slot: ", "property");
            append(slot, "value");
            nl()
            


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


