#!/usr/bin/env python

'''
    Porthole dialogs.simple Package
    Holds common dialog functions for Porthole

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor
    Brian Dolbec, Wm. F. Wheeler, Tommy Iorns

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


from gettext import gettext as _

import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk

#from porthole.utils import debug

class CommonDialog(gtk.Dialog):
    """ A common gtk Dialog class """
    def __init__(self, title, parent, message, callback, button):
        gtk.Dialog.__init__(self, title, parent, gtk.DIALOG_MODAL or
                            gtk.DIALOG_DESTROY_WITH_PARENT, (str(button), 0))
        # add message
        text = gtk.Label(message)
        text.set_padding(5, 5)
        text.show()
        self.vbox.pack_start(text)
        # register callback
        if not callback:
            callback = self.__callback
        self.connect("response", callback)
        self.show_all()
    
    def __callback(self, widget, response):
        # If no callback is given, just remove the dialog when clicked
        self.destroy()

class YesNoDialog(CommonDialog):
    """ A simple yes/no dialog class """
    def __init__(self, title, parent = None,
                 message = None, callback = None):
        CommonDialog.__init__(self, title, parent, message,
                                           callback, _("_Yes"))
        # add "No" button
        self.add_button(_("_No"), 1)
        

class SingleButtonDialog(CommonDialog):
    """ A simple please wait dialog class """
    def __init__(self, title, parent = None, message = None,
                 callback = None, button = None, progressbar = False):
        CommonDialog.__init__(self, title, parent, message,
                                           callback, button)
        if progressbar:
            self.progbar = gtk.ProgressBar()
            self.progbar.set_text(_("Loading"))
            self.progbar.show()
            self.vbox.add(self.progbar)

