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

import threading, re, sys #if this fails... lol
try:
    import pygtk
    pygtk.require("2.0") #make sure we have the right version
except ImportError:
    sys.exit("Error loading libraries!\nIs pygtk installed?")
try:
    import gtk, gtk.glade, gobject, pango
except ImportError:
    sys.exit("Error loading libraries!\nIs GTK+ installed?")
try:
    import portagelib
except ImportError:
    sys.exit("Error loading libraries!\nCan't find portagelib!")
try:
    import process
except ImportError:
    sys.exit("Error loading libraries!\nCan't find process!")

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
            "on_package_view_cursor_changed" : self.package_changed,
            "view_filter_changed" : self.view_filter_changed
            }
        self.wtree.signal_autoconnect(callbacks)
        # aliases for convenience
        self.package_view = self.wtree.get_widget("package_view")
        self.category_view = self.wtree.get_widget("category_view")
        #setup our treemodels
        self.category_model = None
        self.package_model = None
        self.search_results = gtk.TreeStore(gobject.TYPE_STRING,
                                            gtk.gdk.Pixbuf,
                                            gobject.TYPE_PYOBJECT) # Package
        # don't know how to read size from TreeStore
        self.search_results.size = 0
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
        self.category_view.append_column(category_column)
        #set package treeview header
        package_column = gtk.TreeViewColumn("Packages")
        package_pixbuf = gtk.CellRendererPixbuf()
        package_column.pack_start(package_pixbuf, expand = False)
        package_column.add_attribute(package_pixbuf, "pixbuf", 1)
        package_text = gtk.CellRendererText()
        package_column.pack_start(package_text, expand = True)
        package_column.add_attribute(package_text, "text", 0)
        self.package_view.append_column(package_column)
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
        table = create(
            {'name': ({'weight': pango.WEIGHT_BOLD,
                       'scale': pango.SCALE_X_LARGE}),
             'description': ({"style": pango.STYLE_ITALIC}),
             'url': ({'foreground': 'blue'}),
             'property': ({'weight': pango.WEIGHT_BOLD}),
             'value': ({})
             })
        # React when user clicks on the homepage url
        tag = table.lookup('url')
        tag.connect("event", self.on_url_event)
        return table
    

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
            self.update_statusbar(self.SHOW_ALL)
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
        self.category_view.set_model(self.category_model)

    def populate_package_tree(self, category):
        '''fill the package tree'''
        view = self.package_view
        self.package_model = gtk.TreeStore(gobject.TYPE_STRING,
                                           gtk.gdk.Pixbuf,
                                           gobject.TYPE_PYOBJECT) # Package
        if not category:
            view.set_model(self.package_model)
            return
        packages = self.db.categories[category]
        names =  portagelib.sort(packages.keys())
        for name in names:
            #go through each package
            iter = self.package_model.insert_before(None, None)
            self.package_model.set_value(iter, 0, name)
            self.package_model.set_value(iter, 2, packages[name])
            #get an icon for the package
            icon = self.get_icon_for_package(packages[name])
            self.package_model.set_value(
                iter, 1,
                view.render_icon(icon,
                                 size = gtk.ICON_SIZE_MENU,
                                 detail = None))
        view.set_model(self.package_model)

    def get_icon_for_package(self, package):
        """Return an icon for a package"""
        installed = package.get_installed()
        #if it's installed, find out if it can be upgraded
        if installed:
            installed.sort()
            latest_installed = installed[len(installed) -1]
            latest_available = package.get_latest_ebuild()
            if latest_installed == latest_available:
                #they are the same version, so you are up to date
                icon = gtk.STOCK_YES
            else:
                #let the user know there is an upgrade available
                icon = gtk.STOCK_GO_FORWARD
        else:
            #just put the STOCK_NO icon
            icon = gtk.STOCK_NO
        return icon

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
        search_term = self.wtree.get_widget("search_entry").get_text()
        if search_term:
            self.search_results.clear()
            re_object = re.compile(search_term, re.I)
            count = 0
            # no need to sort self.db.list; it is already sorted
            for name, data in self.db.list:
                if re_object.search(name):
                    count += 1
                    iter = self.search_results.insert_before(None, None)
                    self.search_results.set_value(iter, 0, name)
                    self.search_results.set_value(iter, 2, data)
                    #set the icon depending on the status of the package
                    icon = self.get_icon_for_package(data)
                    view = self.package_view
                    self.search_results.set_value(
                        iter, 1,
                        view.render_icon(icon,
                                         size = gtk.ICON_SIZE_MENU,
                                         detail = None))
            self.search_results.size = count  # store number of matches
            self.wtree.get_widget("view_filter").set_history(self.SHOW_SEARCH)
            # in case the search view was already active
            self.update_statusbar(self.SHOW_SEARCH)
                
    def help_contents(self, widget):
        """Show the help file contents."""
        pass

    def about(self, widget):
        """Show about dialog."""
        dialog = AboutDialog()

    def get_treeview_selection(self, treeview, num):
        """Get the value of whatever is selected in a treeview,
        num is the column"""
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
        package = self.get_treeview_selection(treeview, 2)
        self.update_package_info(package)

    def on_url_event(self, tag, widget, event, iter):
        if event.type == gtk.gdk.BUTTON_RELEASE:
            print self.homepage

    def update_package_info(self, package):
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
        notebook.set_sensitive(package and gtk.TRUE or gtk.FALSE)
        if not package:
            #it's really a category selected!
            return
        #put the info into the textview!
        notebook.set_sensitive(gtk.TRUE)
        #set the package
        package.read_description()
        package.read_versions()
        #read it's info
        description = package.description
        metadata = package.get_metadata()
        ebuild = package.get_latest_ebuild()
        installed = package.get_installed()
        versions = package.versions; versions.sort()
        homepage = package.get_homepage()
        self.homepage = homepage  # store url for on_url_event
        use_flags = package.get_use_flags()
        license = package.get_license()
        slot = str(package.get_slot())
        #build the information together into a buffer
        ''' TODO:
            get dependencies and show them in the dependency tab/textview
            figure out what to put into the extras tab...?
        '''
        append(package.get_name(), "name"); nl()
        if description:
            append(description, "description"); nl()
        if metadata and metadata.longdescription:
            nl();
            # longdescription is unicode
            # Todo: don't mix 8-bit and unicode like this
            append(metadata.longdescription.encode("ascii", "replace"),
                   "description")
            nl()
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

    SHOW_ALL = 0
    SHOW_INSTALLED = 1
    SHOW_SEARCH = 2
    def view_filter_changed(self, widget):
        index = widget.get_history()
        self.update_statusbar(index)
        if index == self.SHOW_ALL:
            self.wtree.get_widget("category_scrolled_window").show()
            self.package_view.set_model(self.package_model)
            self.update_package_info(None)
        elif index == self.SHOW_INSTALLED:
            pass
        elif index == self.SHOW_SEARCH:
            self.wtree.get_widget("category_scrolled_window").hide()
            self.package_view.set_model(self.search_results)            

    def update_statusbar(self, mode):
        text = "(undefined)"
        if mode == self.SHOW_ALL:
            text = "%d packages in %d categories" % (len(self.db.list),
                                                     len(self.db.categories))
        elif mode == self.SHOW_INSTALLED:
            pass
        elif mode == self.SHOW_SEARCH:
            text = "%d matches found" % self.search_results.size
        self.set_statusbar(text)

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


