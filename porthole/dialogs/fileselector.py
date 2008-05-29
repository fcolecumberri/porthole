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
