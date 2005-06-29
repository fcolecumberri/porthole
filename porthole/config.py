#!/usr/bin/env python

'''
    Porthole Configuration Dialog
    Allows the user to Configure Porthole

    Copyright (C) 2005 Brian Dolbec, Thomas Iorns

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

import gtk
from utils import dprint

class ConfigDialog:
    """Class to display a GUI for configuring Porthole"""

    def __init__(self, prefs):
        """ Initialize Config GUI """
        # Preserve passed parameters
        self.prefs = prefs
        
        # Parse glade file
        self.gladefile = prefs.DATA_PATH + "config.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "config", self.prefs.APP)
     
        # register callbacks
        callbacks = {
            "on_config_response" : self.on_config_response,
        }
        
        self.wtree.signal_autoconnect(callbacks)
        self.window = self.wtree.get_widget("config")
        

    #-----------------------------------------------
    # GUI Callback function definitions start here
    #-----------------------------------------------

    def on_config_response(self, dialog_widget, response_id):
        """ Parse dialog response (ok, cancel, apply or help clicked) """
        dprint("CONFIG: on_config_response(): response_id '%s'" % response_id)
        if response_id == gtk.RESPONSE_OK:
            self.window.destroy()
        elif response_id == gtk.RESPONSE_CANCEL:
            self.window.destroy()
        elif response_id == gtk.RESPONSE_APPLY:
            pass
        elif response_id == gtk.RESPONSE_HELP:
            #Display help file with web browser
            load_web_page('file://' + self.prefs.DATA_PATH + 'help/config.html')
        else:
            pass

    #------------------------------------------
    # Support function definitions start here
    #------------------------------------------

