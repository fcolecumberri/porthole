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
from loaders import load_web_page

class ConfigDialog:
    """Class to display a GUI for configuring Porthole"""

    def __init__(self, prefs):
        """ Initialize Config GUI """
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
        
        # build list of widgets and equivalent prefs
        self.build_widget_lists()
        
        # set widget values to values in prefs
        self.set_widget_values()

    #-----------------------------------------------
    # GUI Callback function definitions start here
    #-----------------------------------------------

    def on_config_response(self, dialog_widget, response_id):
        """ Parse dialog response (ok, cancel, apply or help clicked) """
        dprint("CONFIG: on_config_response(): response_id '%s'" % response_id)
        if response_id == gtk.RESPONSE_OK:
            self.apply_widget_values()
            self.window.destroy()
        elif response_id == gtk.RESPONSE_CANCEL:
            self.window.destroy()
        elif response_id == gtk.RESPONSE_APPLY:
            self.apply_widget_values()
            pass
        elif response_id == gtk.RESPONSE_HELP:
            #Display help file with web browser
            load_web_page('file://' + self.prefs.DATA_PATH + 'help/config.html')
        else:
            pass

    #------------------------------------------
    # Support function definitions start here
    #------------------------------------------

    def build_widget_lists(self):
        """ Build lists of widgets and equivalent prefs """
        self.tagnamelist = ['command', 'emerge', 'error', 'info', 'caution',
            'warning', 'note', 'linenumber', 'default']
        self.viewoptions = ['downgradable_fg', 'upgradable_fg', 'normal_fg', 'normal_bg']
    
    def set_widget_values(self):
        """ Set widget attributes based on prefs """
        # Terminal Color Tags
        default = self.prefs.TAG_DICT['default']
        attributes = gtk.TextView().get_default_attributes()
        if default[0]: default_fg = gtk.gdk.color_parse(default[0])
        else: default_fg = attributes.fg_color
        if default[1]:  default_bg = gtk.gdk.color_parse(default[1])
        else:  default_bg = attributes.bg_color
        
        for name in self.tagnamelist:
            color = self.prefs.TAG_DICT[name][0] # fg
            widget = self.wtree.get_widget(name + '_fg')
            if widget:
                if color:
                    widget.set_color(gtk.gdk.color_parse(color))
                else:
                    widget.set_color(default_fg)
            color = self.prefs.TAG_DICT[name][1] # bg
            widget = self.wtree.get_widget(name + '_bg')
            if widget:
                if color:
                    widget.set_color(gtk.gdk.color_parse(color))
                else:
                    widget.set_color(default_bg)
        for name in self.viewoptions:
            color = getattr(self.prefs.views, name)
            widget = self.wtree.get_widget(name)
            if widget:
                if color:
                    widget.set_color(gtk.gdk.color_parse(color))
                else:
                    widget.set_color(default_fg)
    
    def apply_widget_values(self):
        """ Set prefs from widget values """
        pass
    


