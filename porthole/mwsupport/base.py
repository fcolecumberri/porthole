#!/usr/bin/env python

'''
    Porthole Mainwindow Package support class
    Support class and functions for the main interface

    Copyright (C) 2003 - 2011
    Fredrik Arnerup, Brian Dolbec,
    Daniel G. Taylor, Wm. F. Wheeler, Tommy Iorns

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

import gi
gi.require_version("Gtk", "3.0") # make sure we have the right version
from gi.repository import Gtk
from gettext import gettext as _


from porthole import config
from porthole.utils import debug
from porthole import backends
PMS_LIB = backends.portage_lib
from porthole.dialogs.about import AboutDialog
from porthole.dialogs.configure import ConfigDialog
from porthole.loaders.loaders import load_web_page

from porthole.backends.version_sort import ver_match

def check_glade():
    """determine the libglade version installed
    and return the correct glade file to use"""
    porthole_gladefile = "glade/main_window.glade"
    #return porthole_gladefile
    # determine glade version
    versions = PMS_LIB.get_installed("gnome-base/libglade")
    if versions:
        debug.dprint("libglade: %s" % versions)
        old, new = ver_match(versions,
            ["2.0.1", "2.4.9-r99"],
            ["2.5.0", "2.99.99"])
        if old:
            debug.dprint("MAINWINDOW: Check_glade(); Porthole no longer " +
                "supports the older versions\nof libglade.  Please upgrade " +
                "libglade to >=2.5.0 for all GUI features to work")
            porthole_gladefile = "glade/main_window.glade"
            new_toolbar_api = False
        elif new:
            porthole_gladefile = "glade/main_window.glade"
            new_toolbar_api = True
    else:
        debug.dprint("MAINWINDOW: No version list returned for libglade")
        return None, None
    debug.dprint("MAINWINDOW: __init__(); glade file = %s" %porthole_gladefile)
    return porthole_gladefile, new_toolbar_api


class MainBase(object):
    """base MainWindow"""

    def __init__(self):

        config.Prefs.use_gladefile, self.new_toolbar_api = check_glade()
        # setup prefs
        config.Prefs.myarch = PMS_LIB.get_arch()
        debug.dprint("MAINWINDOW: Prefs.myarch = " + config.Prefs.myarch)
        #self.config = configs
        # setup glade
        self.gladefile = config.Prefs.DATA_PATH + config.Prefs.use_gladefile
        self.wtree = Gtk.Builder()
        self.wtree.add_from_file(self.gladefile)
        self.wtree.set_translation_domain(config.Prefs.APP)

        # register callbacks  note: Gtk.mainquit deprecated
        self.callbacks = {
            "on_main_window_destroy" : self.goodbye,
            "on_quit1_activate" : self.quit,
            "on_emerge_package" : self.emerge_btn,
            "on_adv_emerge_package" : self.adv_emerge_btn,
            "on_unmerge_package" : self.unmerge_btn,
            "on_sync_tree" : self.sync_tree,
            "on_upgrade_packages" : self.upgrade_packages,
            "on_package_search" : self.package_search,
            "on_search_entry_activate": self.package_search,
            "on_help_contents" : self.help_contents,
            "on_about" : self.about,
            "view_filter_changed" : self.view_filter_changed,
            "on_search_descriptions1_activate" : self.search_set,
            "on_open_log" : self.open_log,
            "on_run_custom" : self.custom_run,
            "on_reload_db" : self.reload_db,
            "on_re_init_portage" : self.re_init_portage,
            "on_cancel_btn" : self.on_cancel_btn,
            #"on_main_window_size_request" : self.size_update,
            "on_plugin_settings_activate" : self.plugin_settings_activate,
            "on_view_refresh" : self.reload_view,
            "on_root_warning_clicked" : self.check_for_root,
            "on_configure_porthole" : self.configure_porthole,
        }
        self.wtree.connect_signals(self.callbacks)

        # aliases for convenience
        self.mainwindow = self.wtree.get_object("main_window")
        # save the mainwindow widget to Config for use by other modules
        # as a parent window
        config.Mainwindow = self.mainwindow

        # how should we setup our saved menus?
        settings = ["pretend", "fetch", "update", "verbose", "noreplace",
                        "oneshot"] # "search_descriptions1"]
        option = 'empty'
        for option in settings:
            widget = self.wtree.get_object(option)
            state = getattr(config.Prefs.emerge, option) or False
            debug.dprint("MAINWINDOW: __init__(); option = %s, state = %s"
                    %(option, str(state)))
            widget.set_active(state)
            widget.connect("activate", self.emerge_setting_set, option)
        # setup a convienience tuple
        self.tool_widgets = ["emerge_package1", "adv_emerge_package1",
                "unmerge_package1", "btn_emerge", "btn_adv_emerge",
                "btn_unmerge", "btn_sync", "view_refresh", "view_filter"]
        self.widget = {}
        for x in self.tool_widgets:
            self.widget[x] = self.wtree.get_object(x)
            if not self.widget[x]:
                debug.dprint("MAINWINDOW: __init__(); Failure to obtain " +
                        "widget '%s'" %x)
        self.status = None


    def help_contents(self, *widget):
        """Show the help file contents."""
        load_web_page('file://' + config.Prefs.DATA_PATH + 'help/index.html')

    def about(self, *widget):
        """Show about dialog."""
        return AboutDialog()

    def configure_porthole(self, menuitem_widget):
        """Shows the Configuration GUI"""
        return ConfigDialog()

    def re_init_portage(self, *widget):
        """re-initializes the imported portage modules in order to
        see changines in any config files
        e.g. /etc/make.conf USE flags changed"""
        PMS_LIB.reload_portage()
        self.view_filter_changed(self.widget["view_filter"])
        return

    def set_cancel_btn(self, state):
        """function name and parameter says it all"""
        self.wtree.get_object("btn_cancel").set_sensitive(state)

    def size_update(self, widget, event):
        #debug.dprint("MAINWINDOW: size_update(); called.")
        """ Store the window and pane positions """
        config.Prefs.main.width = event.width
        config.Prefs.main.height = event.height
        pos = widget.get_position()
        # note: event has x and y attributes but they
        # do not give the same values as get_position().
        config.Prefs.main.xpos = pos[0]
        config.Prefs.main.ypos = pos[1]
        return

    def confirm_delete(self, *widget, **event):
        """Check that there are no running processes
        & confirm the kill before doing it"""
        if self.process_manager.task_completed:
            self.process_manager.allow_delete = True
            return False
        err = _("Confirm: Kill the Running Process in the Terminal")
        dialog = Gtk.MessageDialog(self.mainwindow, Gtk.DialogFlags.MODAL,
                                Gtk.MessageType.QUESTION,
                                Gtk.ButtonsType.YES_NO, err)
        result = dialog.run()
        dialog.destroy()
        if result != Gtk.ResponseType.YES:
            debug.dprint("TERMINAL: kill(); not killing")
            return True
        #self.process_manager.confirm = False
        if self.process_manager.kill_process(None, False):
            debug.dprint("MAINWINDOW: process killed, destroying window")
            self.process_manager.allow_delete = True
            self.process_manager.window.hide()
        return False


    def quit(self, widget):
        """Confirms there are no running processes before
        calling the gooodbye()"""
        if not self.confirm_delete():
            self.goodbye(None)

    def goodbye(self, *widget):
        """Main window quit function"""
        debug.dprint("MAINWINDOW: goodbye(); quiting now")
        Gtk.main_quit()


