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

import string, threading, os, re, sys #if this fails... lol
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
try:
    import webbrowser
except ImportError:
    print "Web browser module not found, you will not be able to load links"

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
        #setup sudo use
        self.use_sudo = -1
        #setup some textbuffers
        tagtable = self.create_tag_table()
        self.summary_buffer = gtk.TextBuffer(tagtable)
        self.summary_text = self.wtree.get_widget("summary_text")
        self.summary_text.set_buffer(self.summary_buffer)
        self.summary_text.connect("motion_notify_event", self.on_mouse_motion)
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
        #set dependency treeview header
        depend_column = gtk.TreeViewColumn("Dependencies")
        depend_pixbuf = gtk.CellRendererPixbuf()
        depend_column.pack_start(depend_pixbuf, expand = False)
        depend_column.add_attribute(depend_pixbuf, "pixbuf", 1)
        depend_text = gtk.CellRendererText()
        depend_column.pack_start(depend_text, expand = True)
        depend_column.add_attribute(depend_text, "text", 0)
        self.wtree.get_widget("depend_view").append_column(depend_column)
        self.depend_model = gtk.TreeStore(gobject.TYPE_STRING,
                                           gtk.gdk.Pixbuf,
                                           gobject.TYPE_PYOBJECT) # Package
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

    def check_for_root(self, callback = None):
        """figure out if the user can emerge or not..."""
        uid = os.getuid()
        if uid != 0:
            self.sudo_dialog = gtk.Dialog(
                "You are not root!",
                self.wtree.get_widget("main_window"),
                gtk.DIALOG_MODAL or gtk.DIALOG_DESTROY_WITH_PARENT,
                ("_Yes", 0))
            self.sudo_dialog.add_button("_No", 1)
            sudo_text = gtk.Label("Do you want use the sudo command "
                                  "to install programs?")
            sudo_text.set_padding(5, 5)
            self.sudo_dialog.vbox.pack_start(sudo_text)
            sudo_text.show()
            self.sudo_dialog.connect("response", self.sudo_response)
            self.sudo_dialog.show_all()
        else:
            self.use_sudo = 0
        if callback:
            self.sudo_dialog.callback = callback

    def sudo_response(self, widget, response):
        if response == 0:
            self.use_sudo = 1
        else:
            self.use_sudo = 2
        callback = self.sudo_dialog.callback
        self.sudo_dialog.destroy()
        if callback:
            callback(None)

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
        self.url_tag = table.lookup('url')
        self.url_tag.connect("event", self.on_url_event)
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
        #if it's installed, find out if it can be upgraded
        if package.is_installed:
            installed = package.get_installed()
            installed.sort()
            latest_installed = installed[-1]
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

    def setup_command(self, command, callback = None):
        """Setup the command to run with sudo or not at all"""
        if self.use_sudo == -1:
            self.check_for_root(callback)
        else:
            if self.use_sudo:
                if self.use_sudo == 1:
                    process.ProcessWindow("sudo " + command)
                else:
                    print "Sorry, can't do that!"
            else:
                process.ProcessWindow(command)

    def emerge_package(self, widget):
        """Emerge the currently selected package."""
        package = self.get_treeview_selection(
            self.wtree.get_widget("package_view"), 2)
        command = self.setup_command("emerge " + package.get_category() +
            "/" + package.get_name(), self.emerge_package)

    def unmerge_package(self, widget):
        """Unmerge the currently selected package."""
        package = self.get_treeview_selection(
            self.wtree.get_widget("package_view"), 2)
        command = self.setup_command("emerge unmerge " +
            package.get_category() + "/" + package.get_name(),
            self.unmerge_package)

    def sync_tree(self, widget):
        """Sync the portage tree and reload it when done."""
        command = self.setup_command("emerge sync", self.sync_tree)

    def upgrade_packages(self, widget):
        """Upgrade all packages that have newer versions available."""
        command = self.setup_command("emerge -uD world", self.upgrade_packages)

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
        """Catch when the user clicks the url"""
        if event.type == gtk.gdk.BUTTON_RELEASE:
            try: webbrowser.open(self.homepages[0])
            except: pass

    def parse_depends_list(self, depends_list, parent = "Default"):
        """read through the depends list and order it nicely"""
        new_list = []
        for depend in depends_list:
            if depend[len(depend) - 1] == "?":
                if depend[0] != "!":
                    parent = "Using " + depend[:len(depend) - 1]
                else:
                    parent = "Not Using " + depend[1:len(depend) - 1]
            else:
                if depend != "(" and depend != ")":
                    new_list.append((parent, depend))
        return new_list
                    

    def add_depends_to_tree(self, depends_list, parent = None, last_flag = None):
        """Add all dependencies to the tree"""
        depend_view = self.wtree.get_widget("depend_view")
        for use_flag, depend in depends_list:
            if last_flag != use_flag:
                parent_iter = self.depend_model.insert_before(parent, None)
                self.depend_model.set_value(parent_iter, 0, use_flag)
                last_flag = use_flag
            depend_iter = self.depend_model.insert_before(parent_iter, None)
            self.depend_model.set_value(depend_iter, 0, depend)
            icon = self.get_icon_for_package(portagelib.Package(depend))
            self.depend_model.set_value(depend_iter, 1, 
                                    depend_view.render_icon( icon,
                                    size = gtk.ICON_SIZE_MENU,
                                    detail = None))
            if icon != gtk.STOCK_YES:
                pack = portagelib.Package(depend)
                ebuild = pack.get_latest_ebuild()
                depends = string.split(portagelib.get_property(ebuild, "DEPEND"))
                if depends:
                    depends = self.parse_depends_list(depends)
                    self.add_depends_to_tree(depends, depend_iter)

    def on_mouse_motion(self, widget, event, data = None):
        # we need to call get_pointer, or we won't get any more events
        pointer = widget.window.get_pointer()
        x, y, spam = pointer
        view = self.summary_text
        x, y = view.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, x, y)
        i = view.get_iter_at_location(x, y)
        is_url = i.has_tag(self.url_tag)
        self.url_tag.set_property(
            "underline", 
            is_url and pango.UNDERLINE_SINGLE or pango.UNDERLINE_NONE)
        widget.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(
            is_url and gtk.gdk.Cursor(gtk.gdk.HAND2) or None)
        return gtk.FALSE

    def update_package_info(self, package):
        """Update the notebook of information about a selected package"""

        def append(text, tag = None):
            """Append (unicode) text to summary buffer."""
            iter = self.summary_buffer.get_end_iter()
            buffer = self.summary_buffer
            if tag: buffer.insert_with_tags_by_name(iter, text, tag)
            else: buffer.insert(iter, text)

        def nl(): append("\n")
        
        self.summary_buffer.set_text("", 0)
        notebook = self.wtree.get_widget("notebook")
        notebook.set_sensitive(package and gtk.TRUE or gtk.FALSE)
        if not package:
            #it's really a category selected!
            return
        #put the info into the textview!
        notebook.set_sensitive(gtk.TRUE)
        #read it's info
        metadata = package.get_metadata()
        ebuild = package.get_latest_ebuild()
        installed = package.get_installed()
        versions = package.get_versions(); versions.sort()
        props = package.get_properties()
        description = props.description
        homepages = props.get_homepages() # may be more than one
        self.homepages = homepages  # store url for on_url_event
        use_flags = props.get_use_flags()
        license = props.license
        slot = unicode(props.get_slot())
        #get everything ready
        ''' TODO:
            figure out what to put into the extras tab...?
        '''
        #get dependencies and put em in a treeview
        depends = string.split(portagelib.get_property(ebuild, "DEPEND"))
        self.depend_model.clear()
        depend_view = self.wtree.get_widget("depend_view")
        if depends:
            depends = self.parse_depends_list(depends)
            self.add_depends_to_tree(depends)
        else:
            parent_iter = self.depend_model.insert_before(None, None)
            self.depend_model.set_value(parent_iter, 0, "None")
        depend_view.set_model(self.depend_model)
        #build info into buffer
        append(package.full_name, "name"); nl()
        if description:
            append(description, "description"); nl()
        if metadata and metadata.longdescription:
            nl(); append(metadata.longdescription, "description"); nl()
        for homepage in homepages: append(homepage, "url"); nl()
        nl()         #put a space between this info and the rest
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
        nl()         #put a space between this info and the rest, again
        if use_flags:
            append("Use Flags: ", "property")
            append(", ".join(use_flags), "value")
            nl()
        if license:
            append("License: ", "property"); append(license, "value"); nl()
        if slot:
            append("Slot: ", "property"); append(slot, "value"); nl()

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


