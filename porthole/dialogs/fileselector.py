#!/usr/bin/env python

"""
    ============
    | File Save |
    -----------------------------------------------------------
    Copyright (C) 2003 - 2008 Fredrik Arnerup, Brian Dolbec, 
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

    -------------------------------------------------------------------------
    To use this program as a module:
    
        from fileselector import FileSelector
"""

import pygtk; pygtk.require('2.0')
import gtk
import os, os.path

from porthole.utils import debug

# deprecated by gtk+
class FileSel(gtk.FileSelection):
    def __init__(self, title):
        gtk.FileSelection.__init__(self, title)
        self.result = False

    def ok_cb(self, button):
        self.hide()
        if self.ok_func(self.get_filename()):
            self.destroy()
            self.result = True
        else:
            self.show()

    def run(self, parent, start_file, func):
        if start_file:
            self.set_filename(start_file)

        self.ok_func = func
        self.ok_button.connect("clicked", self.ok_cb)
        self.cancel_button.connect("clicked", lambda x: self.destroy())
        self.connect("destroy", lambda x: gtk.main_quit())
        self.set_modal(True)
        self.show()
        gtk.main()
        return self.result

# deprecated by gtk+
class FileSelector:
    """Generic file selector dialog for opening or saving files"""
    
    def __init__(self, parent_window, target_path, callback = None, overwrite_confirm = True):
        self.window = parent_window
        self.callback = callback
        self.overwrite_confirm = overwrite_confirm
        self.filename = ''
        self.directory = target_path

    def _save_as_ok_func(self, filename):
        """file selector callback function"""
        debug.dprint("FILESELECTOR: Entering _save_as_ok_func")
        old_filename = self.filename
        if self.overwrite_confirm and (not self.filename or filename != self.filename):
            if os.path.exists(filename):
                err = _("Ovewrite existing file '%s'?")  % filename
                dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                            gtk.MESSAGE_QUESTION,
                                            gtk.BUTTONS_YES_NO, err);
                result = dialog.run()
                dialog.destroy()
                if result != gtk.RESPONSE_YES:
                    return False

        self.filename = filename
        return True

    def save_as(self, title):
        debug.dprint("FILESELECTOR: Entering save_as()")
        return FileSel(title).run(window, self.filename, self._save_as_ok_func)
        
    def get_filename(self, title):
        debug.dprint("FILESELECTOR: Entering get_filename()")
        result = FileSel(title).run(self.window, self.directory, self._save_as_ok_func)
        if result:
            return self.filename
        else:
            return ''


class FileSelector2:
    """Generic file selector dialog for opening or saving files"""
    
    def __init__(self, parent_window, target_path, callback = None, overwrite_confirm = True, filter = None):
        debug.dprint("FILESELECTOR2: __init__(); # 109 target_path = %s" %str(target_path))
        self.window = parent_window
        self.callback = callback
        self.overwrite_confirm = overwrite_confirm
        if os.path.isdir(target_path):
            self.directory = target_path
            debug.dprint("FILESELECTOR2: __init__(); # 115 directory = %s" %str(self.directory))
            self.target = ''
        elif os.path.isfile(target_path):
            self.target = target_path
            self.directory, file = os.path.split(target_path)
            debug.dprint("FILESELECTOR2: __init__(); # 120 directory = %s" %str(self.directory))
        else:
            self.directory, self.target  =os.path.split(target_path)
            debug.dprint("FILESELECTOR2: __init__(); # 123 directory = %s" %str(self.directory))
        self.filter = filter
        
        self.actions = {'save': gtk.FILE_CHOOSER_ACTION_SAVE,
                                'open': gtk.FILE_CHOOSER_ACTION_OPEN,
                                'select_folder': gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                'create_folder': gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER
                                }


    def create_selector(self, title, action):
        debug.dprint("FILESELECTOR2: Entering create_selector()")
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.dialog = gtk.FileChooserDialog(title, self.window, self.actions[action], buttons)
        self.dialog.set_do_overwrite_confirmation(self.overwrite_confirm)
        if self.directory:
            debug.dprint("FILESELECTOR2: create_selector(); # 142 directory = %s" %str(self.directory))
            self.dialog.set_current_folder(self.directory)
        if self.target and'/' in self.target:
            self.dialog.set_filename(self.target)
        else:
            self.dialog.set_current_name(self.target)
        show_all = gtk.FileFilter()
        show_all.add_pattern('*')
        show_all.set_name('All')
        self.dialog.add_filter(show_all)
        if self.filter: # add a specified filter string
            filter = gtk.FileFilter()
            filter.add_pattern(self.filter)
            filter.set_name(self.filter.split('.')[1] +' Files')
            debug.dprint("FILESELECTOR2: create_selector(); filter name = " + filter.get_name() )
            self.dialog.add_filter(filter)
            self.dialog.set_filter(filter)
        else:
            self.dialog.set_filter(show_all)
        
    def get_filename(self, title, action):
        debug.dprint("FILESELECTOR2: Entering get_filename()")
        self.create_selector(title, action)
        result = self.dialog.run()
        debug.dprint("FILESELECTOR2: get_filename(); result = " + str(result))
        if result in [gtk.RESPONSE_OK, gtk.RESPONSE_ACCEPT, gtk.RESPONSE_YES]: 
            filename = self.dialog.get_filename()
        elif result in [gtk.RESPONSE_CANCEL, gtk.RESPONSE_DELETE_EVENT, gtk.RESPONSE_CLOSE]:
            filename = ''
        self.dialog.destroy()
        debug.dprint("FILESELECTOR2: get_filename(); filename = " + filename)
        return filename
