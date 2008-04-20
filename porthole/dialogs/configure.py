#!/usr/bin/env python

'''
    Porthole Configuration Dialog
    Allows the user to Configure Porthole

    Copyright (C) 2005 - 2008 Brian Dolbec, Thomas Iorns

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

import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, gtk.glade

from porthole.utils import debug
from porthole.loaders.loaders import load_web_page
from porthole import config
from porthole import backends
portage_lib = backends.portage_lib

class ConfigDialog:
    """Class to display a GUI for configuring Porthole"""

    def __init__(self):
        """ Initialize Config GUI """
        
        # Parse glade file
        self.gladefile = config.Prefs.DATA_PATH + "/glade/config.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "config", config.Prefs.APP)
     
        # register callbacks
        callbacks = {
            "on_config_response" : self.on_config_response,
            "on_color_set" : self.on_color_set,
            "on_color_clicked" : self.on_color_clicked,
            "on_enable_archlist_toggled" : self.toggle_archlist,
            "on_globals_use_custom_browser_toggled" : self.toggle_browser_table,
        }
        
        self.window = self.wtree.get_widget("config")
        self.KeywordsFrame = self.wtree.get_widget("archlist_frame")
        self.wtree.signal_autoconnect(callbacks)
       
        # Hide widgets which haven't been implemented yet
        self.hide_widgets()
        
        # build list of widgets and equivalent prefs
        self.build_widget_lists()
        
        # set widget values to values in prefs
        self.set_widget_values()

    #-----------------------------------------------
    # GUI Callback function definitions start here
    #-----------------------------------------------

    def on_config_response(self, dialog_widget, response_id):
        """ Parse dialog response (ok, cancel, apply or help clicked) """
        debug.dprint("CONFIGDIALOG: on_config_response(): response_id '%s'" % response_id)
        if response_id == gtk.RESPONSE_OK:
            self.apply_widget_values()
            self.window.destroy()
        elif response_id == gtk.RESPONSE_CANCEL:
            self.window.destroy()
        elif response_id == gtk.RESPONSE_APPLY:
            self.apply_widget_values()
        elif response_id == gtk.RESPONSE_HELP:
            #Display help file with web browser
            load_web_page('file://' + config.Prefs.DATA_PATH + 'help/customize.html')
        else:
            pass
    
    def on_color_clicked(self, button_widget, event):
        """ Make sure colour dialog doesn't show alpha choice """
        debug.dprint("CONFIGDIALOG: on_color_clicked()")
        if event.button == 1: # primary mouse button
            button_widget.set_use_alpha(False)
            return False # continue to build colour selection dialog
        if event.button == 3: # secondary mouse button
            if button_widget.get_alpha() > 40000:
                button_widget.set_alpha(32767)
                button_widget.set_use_alpha(True)
                name = button_widget.get_property('name')
                if name == 'default_fg':
                    button_widget.set_color(self.default_textview_fg)
                elif name == 'default_bg':
                    button_widget.set_color(self.default_textview_bg)
                else:
                    ext = name[-3:]
                    color = self.wtree.get_widget('default' + ext).get_color()
                    button_widget.set_color(color)
                self.on_color_set(button_widget)
                return True
            else:
                button_widget.set_alpha(65535)
                button_widget.set_use_alpha(False)
                self.on_color_set(button_widget)
                return True
    
    def on_color_set(self, button_widget):
        debug.dprint("CONFIGDIALOG: on_color_set()")
        # if button is default-button: change colour in all buttons using default.
        color = button_widget.get_color()
        ext = None
        if button_widget.get_property('name') == 'default_fg':
            ext = "fg"
        elif button_widget.get_property('name') == 'default_bg':
            ext = "bg"
        if not ext or not hasattr(self, 'tagnamelist'):
            return
        for name in self.tagnamelist:
            widget = self.wtree.get_widget('_'.join([name, ext]))
            if widget:
                if widget.get_alpha() < 40000:
                    widget.set_color(color)

    #------------------------------------------
    # Support function definitions start here
    #------------------------------------------

    def hide_widgets(self):
        # hide unimplemented widgets
        hidelist = [ # widget names
            'label_custom_editor',
            'custom_editor_command',
            'main_font_box',
            'lang_box',
            'sample_scrolled_window_1',
            'sample_label_1',
            'sample_scrolled_window_2',
            'sample_label_2',
        ]
        for name in hidelist:
            widget = self.wtree.get_widget(name)
            if widget:
                widget.hide_all()
        # hide unimplemented notebook tabs
        removelist = [ # [notebook, tab to remove]
            ['terminal_notebook', 'filter_tab'],
            ['main_window_notebook', 'category_view_tab'],
            ['main_window_notebook', 'package_view_tab'],
        ]
        for notebook, tab in removelist:
            notewidget = self.wtree.get_widget(notebook)
            tabwidget = self.wtree.get_widget(tab)
            tabnum = notewidget.page_num(tabwidget)
            notewidget.remove_page(tabnum)
        return
    
    def build_widget_lists(self):
        """ Build lists of widgets and equivalent prefs """
        self.tagnamelist = ['command', 'emerge', 'error', 'info', 'caution',
            'warning', 'note', 'linenumber', 'default']
        self.xtermtaglist = ['black', 'red', 'green', 'yellow', 'blue',
            'magenta', 'cyan', 'white']
        self.viewoptions = ['downgradable_fg', 'upgradable_fg', 'normal_fg', 'normal_bg']
        self.checkboxes = [
            ['summary', 'showtable'],
            ['summary', 'showkeywords'],
            ['summary', 'showavailable'],
            ['summary', 'showinstalled'],
            ['summary', 'showlongdesc'],
            ['summary', 'showuseflags'],
            ['summary', 'showlicense'],
            ['summary', 'showurl'],
            ['emerge', 'pretend'],
            ['emerge', 'verbose'],
            ['emerge', 'nospinner'],
            ['emerge', 'fetch'],
            ['emerge', 'upgradeonly'],
            ['globals', 'enable_archlist'],
            ##['globals', 'enable_all_keywords'],
            ['globals', 'use_custom_browser'],
            ['advemerge', 'show_make_conf_button'],
        ]
        self.syncmethods = config.Prefs.globals.Sync_methods
    
    def set_widget_values(self):
        """ Set widget attributes based on prefs """
        
        # Display current CPU architecture
        widget = self.wtree.get_widget('current_arch')
        widget.set_label(config.Prefs.myarch)
        
        # Terminal Color Tags
        default = config.Prefs.TAG_DICT['default']
        attributes = gtk.TextView().get_default_attributes()
        self.default_textview_fg = attributes.fg_color
        self.default_textview_bg = attributes.bg_color
        if default[0]: default_fg = gtk.gdk.color_parse(default[0])
        else: default_fg = self.default_textview_fg
        if default[1]: default_bg = gtk.gdk.color_parse(default[1])
        else: default_bg = self.default_textview_bg
        
        for name in self.tagnamelist:
            color = config.Prefs.TAG_DICT[name][0] # fg
            widget = self.wtree.get_widget(name + '_fg')
            if widget:
                if color:
                    widget.set_color(gtk.gdk.color_parse(color))
                else:
                    widget.set_color(default_fg)
                    widget.set_alpha(32767) # to show it's using the default value
                    widget.set_use_alpha(True)
            color = config.Prefs.TAG_DICT[name][1] # bg
            widget = self.wtree.get_widget(name + '_bg')
            if widget:
                if color:
                    widget.set_color(gtk.gdk.color_parse(color))
                else:
                    widget.set_color(default_bg)
                    widget.set_alpha(32767) # to show it's using the default value
                    widget.set_use_alpha(True)
        
        # Terminal Font:
        widget = self.wtree.get_widget('terminal_font')
        if widget:
            if config.Prefs.terminal.font:
                widget.set_font_name(config.Prefs.terminal.font)
            self.terminal_font = widget.get_font_name()
        
        # Default XTerm colours:
        for name in self.xtermtaglist:
            color = config.Prefs.TAG_DICT['fg_' + name][0]
            widget = self.wtree.get_widget('fg_' + name)
            if widget:
                if color:
                    widget.set_color(gtk.gdk.color_parse(color))
                else: # this should never happen, but just in case...
                    widget.set_color(gtk.gdk.color_parse(name))
            color = config.Prefs.TAG_DICT['bg_' + name][1]
            widget = self.wtree.get_widget('bg_' + name)
            if widget:
                if color:
                    widget.set_color(gtk.gdk.color_parse(color))
                else: # this should never happen, but just in case...
                    widget.set_color(gtk.gdk.color_parse(name))
        
        # View Colours
        for name in self.viewoptions:
            color = getattr(config.Prefs.views, name)
            widget = self.wtree.get_widget(name)
            if widget:
                if color:
                    widget.set_color(gtk.gdk.color_parse(color))
                else:
                    widget.set_color(default_fg)
        
        # Checkboxes:
        for category, name in self.checkboxes:
            widget = self.wtree.get_widget('_'.join([category, name]))
            debug.dprint("CONFIGDIALOG: set_widget_values(); Checkboxes: widget = %s" %('_'.join([category, name])))
            if widget:
                active = getattr(getattr(config.Prefs, category), name)
                debug.dprint(str(active))
                if active == []:
                    active = False
                widget.set_active(active)
            else:
                debug.dprint("CONFIGDIALOG: set_widget_values(); Checkboxes: widget = %s not found!" %('_'.join([category, name])))
        
        # Sync combobox
        store = gtk.ListStore(str)
        widget = self.wtree.get_widget('sync_combobox')
        tempiter = None
        if widget:
            for command, label in self.syncmethods:
                if not command.startswith('#'):
                    tempiter = store.append([command])
                    if command == config.Prefs.globals.Sync:
                        iter = tempiter
            widget.set_model(store)
            cell = gtk.CellRendererText()
            widget.pack_start(cell, True)
            widget.add_attribute(cell, 'text', 0)
            if tempiter:
                widget.set_active_iter(iter)
        
        # Custom Command History
        for x in [1, 2, 3, 4, 5]:
            widget = self.wtree.get_widget('history' + str(x))
            if widget:
                pref = config.Prefs.run_dialog.history[x]
                widget.set_text(pref)
        
        # custom browser command
        widget = self.wtree.get_widget('custom_browser_command')
        if widget:
            command = config.Prefs.globals.custom_browser_command
            if command:
                widget.set_text(command)
            if not config.Prefs.globals.use_custom_browser:
                self.wtree.get_widget('custom_browser_table').set_sensitive(False)
                
        # gui su client command
        widget = self.wtree.get_widget('su_client')
        if widget:
            command = config.Prefs.globals.su
            if command:
                widget.set_text(command)
        
        # build the arch list widget
        self.build_archlist_widget()
        
    
    def apply_widget_values(self):
        """ Set prefs from widget values """
        # Terminal Color Tags
        for name in self.tagnamelist:
            widget = self.wtree.get_widget(name + '_fg')
            if widget:
                color = widget.get_color()
                alpha = widget.get_alpha()
                #debug.dprint("CONFIGDIALOG: '%s_fg': previous value: '%s'" % (name, config.Prefs.TAG_DICT[name][0]))
                if alpha > 40000: # colour set
                    #debug.dprint("CONFIGDIALOG: setting to '%s'" % self.get_color_spec(color))
                    config.Prefs.TAG_DICT[name][0] = self.get_color_spec(color)
                else: # use default
                    #debug.dprint("CONFIGDIALOG: setting to ''")
                    config.Prefs.TAG_DICT[name][0] = ''
            widget = self.wtree.get_widget(name + '_bg')
            if widget:
                color = widget.get_color()
                alpha = widget.get_alpha()
                #debug.dprint("CONFIGDIALOG: '%s_bg': previous value: '%s'" % (name, config.Prefs.TAG_DICT[name][1]))
                if alpha > 40000:
                    #debug.dprint("CONFIGDIALOG: setting to '%s'" % self.get_color_spec(color))
                    config.Prefs.TAG_DICT[name][1] = self.get_color_spec(color)
                else:
                    #debug.dprint("CONFIGDIALOG: setting to ''")
                    config.Prefs.TAG_DICT[name][1] = ''
        
        # Terminal Font:
        widget = self.wtree.get_widget('terminal_font')
        if widget and self.terminal_font != widget.get_font_name():
            config.Prefs.terminal.font = widget.get_font_name()
        
        # Default XTerm colours:
        for name in self.xtermtaglist:
            widget = self.wtree.get_widget('fg_' + name)
            if widget:
                color = widget.get_color()
                if color:
                    config.Prefs.TAG_DICT['fg_' + name][0] = self.get_color_spec(color)
            widget = self.wtree.get_widget('bg_' + name)
            if widget:
                color = widget.get_color()
                if color:
                    config.Prefs.TAG_DICT['bg_' + name][1] = self.get_color_spec(color)
                else: # this should never happen, but just in case...
                    widget.set_color(gtk.gdk.color_parse(name))
        
        # View Colours
        for name in self.viewoptions:
            widget = self.wtree.get_widget(name)
            if widget:
                color = widget.get_color()
                alpha = widget.get_alpha()
                if alpha:
                    setattr(config.Prefs.views, name, self.get_color_spec(color))
                else:
                    setattr(config.Prefs.views, name, '')
        
        # Checkboxes:
        for category, name in self.checkboxes:
            debug.dprint("CONFIGDIALOG: apply_widget_values(); name = %s" %name)
            widget = self.wtree.get_widget('_'.join([category, name]))
            if widget:
                #debug.dprint("CONFIGDIALOG: apply_widget_values(); name = %s widget found" %name)
                active = widget.get_active()
                setattr(getattr(config.Prefs, category), name, active)
                if name == 'enable_archlist' and active:
                    archlist = []
                    keyword = ''
                    for item in self.kwList:
                        keyword = item[1]
                        if item[0].get_active():
                            debug.dprint(item[1])
                            archlist.append(keyword)
                    debug.dprint("CONFIGDIALOG: new archlist = %s" %str(archlist))
                    config.Prefs.globals.archlist = archlist[:]
            
        
        # Sync combobox
        widget = self.wtree.get_widget('sync_combobox')
        if widget:
            model = widget.get_model()
            iter = widget.get_active_iter()
            sync_command = model.get_value(iter, 0)
            for command, label in self.syncmethods:
                if command == sync_command:
                    config.Prefs.globals.Sync = command
                    config.Prefs.globals.Sync_label = label
                    break
        
        # Custom Command History
        for x in [1, 2, 3, 4, 5]:
            widget = self.wtree.get_widget('history' + str(x))
            if widget:
                text = widget.get_text()
                if text != config.Prefs.run_dialog.history[x]:
                    config.Prefs.run_dialog.history[x] = text
        
        # custom browser command
        widget = self.wtree.get_widget('custom_browser_command')
        if widget:
            text = widget.get_text()
            if text:
                config.Prefs.globals.custom_browser_command = text
        
        # gui su client command
        widget = self.wtree.get_widget('su_client')
        if widget:
            text = widget.get_text()
            if text:
                config.Prefs.globals.su = text
        

    def get_color_spec(self, color):
        red = hex(color.red)[2:].zfill(4)
        green = hex(color.green)[2:].zfill(4)
        blue = hex(color.blue)[2:].zfill(4)
        return '#' + red + green + blue
    
    def build_archlist_widget(self):
        """ Create a table layout and populate it with 
            checkbox widgets representing the available
            keywords
        """
        debug.dprint("CONFIGDIALOG: build_archlist_widget()")

        # If frame has any children, remove them
        child = self.KeywordsFrame.child
        if child != None:
            self.KeywordsFrame.remove(child)

        keywords = portage_lib.get_archlist()
        
        # Build table to hold radiobuttons
        size = len(keywords)
        maxcol = 3
        maxrow = size / maxcol - 1
        if maxrow < 1:
            maxrow = 1
        table = gtk.Table(maxrow, maxcol-1, True)
        self.KeywordsFrame.add(table)
        self.kwList = []

        # Iterate through use flags collection, create 
        # checkboxes and attach to table
        col = 0
        row = 0
        button_added = False
        clickable_button = False
        for keyword in keywords:
            button = gtk.CheckButton(keyword)
            self.kwList.append([button, keyword])
            table.attach(button, col, col+1, row, row+1)
            button.show()
            button_added = True
            clickable_button = True
            button.set_active(keyword in config.Prefs.globals.archlist)
            # Increment col & row counters
            if button_added:
                col += 1
                if col > maxcol:
                    col = 0
                    row += 1
        if clickable_button:
            # Display the entire table
            table.show()
            self.KeywordsFrame.show()
            self.KeywordsFrame.set_sensitive(config.Prefs.globals.enable_archlist)
        else:
            self.KeywordsFrame.set_sensitive(False)
        debug.dprint("CONFIGDIALOG: build_archlist_widget(); widget build completed")
        
    def toggle_archlist(self, widget):
        """Toggles the archlist frame sensitivity
        """
        debug.dprint("CONFIGDIALOG: toggle_archlist(); signal caught")
        self.KeywordsFrame.set_sensitive(widget.get_active())
        config.Prefs.globals.enable_archlist = widget.get_active()

    def toggle_browser_table(self, widget):
        """Toggles custom browser command sensitivity
        """
        debug.dprint("CONFIGDIALOG: toggle_browser_table()")
        self.wtree.get_widget('custom_browser_table').set_sensitive(widget.get_active())


