#!/usr/bin/env python

"""
    ============
    | Terminal Notebook |
    -----------------------------------------------------------
    A graphical multipage notebook class
    -----------------------------------------------------------
    Copyright (C) 2003 - 2009 Fredrik Arnerup, Brian Dolbec, 
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
    
        from notebook import TerminalNotebook
"""
import pygtk; pygtk.require('2.0')
import gtk, pango

from porthole.terminal.constants import *
from porthole.utils import debug
from porthole import config

class TerminalNotebook:
    """generates a terminal notebook structure containing all needed views,
    buffers,handler id's, etc."""

    def __init__( self, notebook = None, wtree = None, set_statusbar = None): # all arrays follow the same TABS order
        self.notebook = notebook
        self.wtree = wtree
        self.set_statusbar = set_statusbar
        self.view = [] #[None, None, None, None]
        self.scrolled_window = [] #[None, None, None, None, None]
        self.view_buffer = [] #[None, None, None, None]
        self.view_buffer_types = {TAB_PROCESS:"log",
                                         TAB_WARNING:"warning",
                                         TAB_CAUTION:"caution",
                                         TAB_INFO:"summary",
                                         TAB_QUEUE:None}
        self.tab = [] #[None, None, None, None]
        self.visible_tablist = []
        self.tab_showing = [True, False, False, False, False] # initialize to default state
        self.current_tab = 0
        self.vadjustment = [] #[None, None, None, None, None]
        self.vhandler_id = [] #[None, None, None, None, None]
        self.auto_scroll = [True, False, False, False, False]
        self.end_mark = [] # hold the end of buffer text marks for autoscrolling
        self.last_text = [] # keep a record of the last text entered
        self.get_tab_list() # initialize to default state

        # save the tab contents and remove them until we need em
        self.warning_tab = self.notebook.get_nth_page(TAB_WARNING)
        self.caution_tab = self.notebook.get_nth_page(TAB_CAUTION)
        self.info_tab = self.notebook.get_nth_page(TAB_INFO)
        self.queue_tab = self.notebook.get_nth_page(TAB_QUEUE)
        self.notebook.remove_page(TAB_QUEUE)
        self.notebook.remove_page(TAB_INFO)
        self.notebook.remove_page(TAB_CAUTION)
        self.notebook.remove_page(TAB_WARNING)

        # get the buffer & view widgets and assign them to their arrays
        widget_labels = ["process_text", "warnings_text", "cautions_text", "info_text"]
        for x in widget_labels:
            buff = self.wtree.get_widget(x).get_buffer()
            self.view_buffer += [buff]
            view = self.wtree.get_widget(x)
            self.view += [view]
            self.last_text += ['\n']
            #if x == "process_text" or config.Prefs.terminal.all_tabs_use_custom_colors:
            fg, bg, weight = config.Prefs.TAG_DICT['default']
            font = config.Prefs.terminal.font
            if bg: view.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(bg))
            if fg: view.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(fg))
            if font: view.modify_font(pango.FontDescription(font))
        del buff
        widget_labels = ["scrolledwindow2", "scrolledwindow8", "scrolledwindow7",
                         "scrolledwindow5", "scrolledwindow4"]
        for x in widget_labels:
            window = self.wtree.get_widget(x)
            self.scrolled_window += [window]
        del x
        
        # Catch button events on info, caution & warning tabs
        # Following a double click on a line, bring that line
        # in the process window into focus near center screen
        self.view[TAB_INFO].connect("button_press_event", self.button_event)
        self.view[TAB_CAUTION].connect("button_press_event", self.button_event)
        self.view[TAB_WARNING].connect("button_press_event", self.button_event)        
        self.view[TAB_INFO].connect("button_release_event", self.button_event)
        self.view[TAB_CAUTION].connect("button_release_event", self.button_event)
        self.view[TAB_WARNING].connect("button_release_event", self.button_event)
        # Initialize event widget source
        self.event_src = None

        # Set formatting tags now that tabs are established
        self.current_tagnames = ['default']
        self.esc_seq_dict = {}
        self.set_tags()
        # text mark to mark the start of the current command
        self.command_start = None

        debug.dprint("NOTEBOOK: get & connect to vadjustments")
        #debug.dprint(TABS[:-1])
        for x in TABS[:-1]:
            #debug.dprint(x)
            adj = self.scrolled_window[x].get_vadjustment()
            self.vadjustment +=  [adj]
            id = self.vadjustment[x].connect("value_changed", self.set_scroll)
            self.vhandler_id += [id]
            #self.auto_scroll[x] = False  # already initialized to True
            # create autoscroll end marks to seek to &
            end_mark = self.view_buffer[x].create_mark(("end_mark"+str(x)), self.view_buffer[x].get_end_iter(), False)
            self.end_mark += [end_mark]
        #debug.dprint("NOTEBOOK: __init__() -- self.vadjustment[]," +
        #       "self.vhandler_id[], self.autoscroll")
        #debug.dprint(self.vadjustment)
        #debug.dprint(self.vhandler_id)
        #debug.dprint(self.auto_scroll)
        self.notebook.connect("switch-page", self.switch_page)


    def get_tab_list(self):
        """creates the current notebook tab list"""
        #tabs_showing = 0
        self.visible_tablist = []
        tab_num = 0
        #debug.dprint("NOTEBOOK: get_tab_list -- self.tab_showing")
        #debug.dprint(self.tab_showing)
        for tab in self.tab_showing:
            #debug.dprint(tab_num)
            #debug.dprint(tab)
            if tab:
                self.visible_tablist += [tab_num]
            tab_num += 1
        debug.dprint("NOTEBOOK: get_tab_list() new self.visible_tablist: %s" % self.visible_tablist)
        return

    def get_current_vadjustment_value(self):
        """gets the value for the currently showing tab"""
        return self.vadjustment[self.current_tab].get_value()

    def show_tab(self, tab):
        """ Create the label for the tab and show it """
        if self.tab_showing[tab]:
            return
        # this hbox will hold the icon and label
        hbox = gtk.HBox()
        icon = gtk.Image()
        # set the icon, label, tab, and position of the tab
        if tab == TAB_WARNING:
            icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)
            label, tab, pos = _(TAB_LABELS[TAB_WARNING]), self.warning_tab, 1
            self.tab_showing[TAB_WARNING] = True
        elif tab == TAB_CAUTION:
            icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)
            label, tab = _(TAB_LABELS[TAB_CAUTION]), self.caution_tab
            # quick hack to make it always show before info & queue tabs
            pos = self.notebook.page_num(self.info_tab)
            if pos == -1:
                pos = self.notebook.page_num(self.queue_tab)
                if pos == -1:
                    pos = 2
            self.tab_showing[TAB_CAUTION] = True
        elif tab == TAB_INFO:
            icon.set_from_stock(gtk.STOCK_DIALOG_INFO, gtk.ICON_SIZE_MENU)
            label, tab = _(TAB_LABELS[TAB_INFO]), self.info_tab
            pos = self.notebook.page_num(self.queue_tab)
            # set to show before queue tab
            if pos == -1: pos = 3
            self.tab_showing[TAB_INFO] = True
        elif tab == TAB_QUEUE:
            icon.set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            label, tab, pos = _(TAB_LABELS[TAB_QUEUE]), self.queue_tab, 4
            self.tab_showing[TAB_QUEUE] = True
        # pack the icon and label onto the hbox
        hbox.pack_start(icon)
        hbox.pack_start(gtk.Label(label))
        hbox.show_all()
        # insert the tab
        self.notebook.insert_page(tab, hbox, pos)
        # reset the visible_tablist
        self.get_tab_list()
        debug.dprint("NOTEBOOK: self.visible_tablist %s" % self.visible_tablist)
        
    def hide_tab(self, tab):
        pos = -1
        if tab == TAB_WARNING:
            pos = self.notebook.page_num(self.warning_tab)
        elif tab == TAB_CAUTION:
            pos = self.notebook.page_num(self.caution_tab)
        elif tab == TAB_INFO:
            pos = self.notebook.page_num(self.info_tab)
        elif tab == TAB_QUEUE:
            pos = self.notebook.page_num(self.queue_tab)
        if pos is not -1:
            debug.dprint("NOTEBOOK: hiding tab %s, pos %s." % (tab, pos))
            self.notebook.remove_page(pos)
            self.tab_showing[tab] = False

    def copy_selected(self, *widget):
        """ Copy selected text to clipboard """
        self.view_buffer[self.current_tab].copy_clipboard(self.clipboard)
        pass

    def clear_buffers(self, *widget):
        """ Clear the text buffers """
        self.view_buffer[TAB_PROCESS].set_text('')
        self.view_buffer[TAB_WARNING].set_text('')
        self.view_buffer[TAB_CAUTION].set_text('')
        self.view_buffer[TAB_INFO].set_text('')
        self.view_buffer[TAB_PROCESS].set_modified(False)
        self.view_buffer[TAB_WARNING].set_modified(False)
        self.view_buffer[TAB_CAUTION].set_modified(False)
        self.view_buffer[TAB_INFO].set_modified(False)

    def button_event(self, widget, event):
        """ Catch button events.  When a dbl-click occurs save the widget
            as the source.  When a corresponding button release from the same
            widget occurs, move to the process window and jump to the line
            number clicked on.
        """
        if event.type == gtk.gdk._2BUTTON_PRESS:
            # Capture the source of the dbl-click event
            # but do nothing else
            self.event_src = widget

        elif event.type == gtk.gdk.BUTTON_RELEASE and \
            self.event_src == widget:
            # clear the event source to prevent false restarts
            self.event_src = None
            # The button release event following the dbl-click
            # from the same widget, go ahead and process now
            # Convert x,y window coords to buffer coords and get line text
            x = int(event.x)
            y = int(event.y)
            bufcoords = widget.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT,x,y)
            # Set start iter at beginning of line (0)
            iStart = widget.get_iter_at_location(0,bufcoords[1])
            # Set end iter far enough right to grab number (100)
            iEnd = widget.get_iter_at_location(100,bufcoords[1])
            try:
                # get line number from textbuffer (0 based)
                # we'll do this inside a try clause in case the user
                # clicks on a line without a number or anything else
                # goes wrong!
                line = int(iStart.get_text(iEnd)[0:6]) - 1 
                # Get the iter based on the line number index
                iter = self.view_buffer[TAB_PROCESS].get_iter_at_line_index(line,0)
                # Scroll to the line, try to position mid-screen
                self.view[TAB_PROCESS].scroll_to_iter(iter, 0.0, True, 0, 0.5)
                # Turn off auto scroll
                self.auto_scroll[TAB_PROCESS] = False
                # Display the tab
                self.notebook.set_current_page(TAB_PROCESS)
            except: pass
        return False  # Always return false for proper handling

    def set_scroll(self,  vadjustment):
        """Sets autoscrolling on when moved to bottom of scrollbar"""
        #debug.dprint("NOTEBOOK: set_scroll() -- vadjustment")
        self.auto_scroll[self.current_tab] = ((vadjustment.upper - \
                                                        vadjustment.get_value()) - \
                                                        vadjustment.page_size < \
                                                         (SLIDER_CLOSE_ENOUGH * vadjustment.page_size))
        return

    def switch_page(self, notebook, page, page_num):
        """callback function changes the current_page setting in the term structure"""
        debug.dprint("NOTEBOOK: switch_page(); page_num = " + str(page_num))
        self.current_tab = self.visible_tablist[page_num]
        if self.auto_scroll[self.current_tab]:
            self.scroll_current_view()
        return

    def scroll_current_view(self):
        """scrolls the current_tab"""
        if self.current_tab != TAB_QUEUE:
            self.view[self.current_tab].scroll_mark_onscreen(self.end_mark[self.current_tab])

    def set_tags(self):
        """ set the text formatting tags from prefs object """
        # NOTE: for ease of maintenance, all tabs have every tag
        #       defined for use.  Currently the code determines
        #       when & where to use the tags
        for process_tab in [TAB_PROCESS, TAB_WARNING, TAB_CAUTION, TAB_INFO]:
            bounds = self.view_buffer[process_tab].get_bounds()
            self.view_buffer[process_tab].remove_all_tags(*bounds)
            for key in config.Prefs.TAG_DICT:
                text_tag = config.Prefs.TAG_DICT[key] 
                argdict = {}
                if text_tag[0]:
                    argdict["foreground"] = text_tag[0]
                if text_tag[1]:
                    argdict["background"] = text_tag[1]
                if text_tag[2]:
                    argdict["weight"] = text_tag[2]
                if key == 'default':
                    argdict = {} # already set as default for textview
                tag_table = self.view_buffer[process_tab].get_tag_table()
                foundtag = tag_table.lookup(key)
                if foundtag:
                    tag_table.remove(foundtag)
                self.view_buffer[process_tab].create_tag(key, **argdict)
        # shell format codes. Values defined with other tags in prefs.
        self.esc_seq_dict = { \
            0  : 'default',
            1  : 'bold',
            2  : 'light',
            30 : 'fg_black',
            31 : 'fg_red',
            32 : 'fg_green',
            33 : 'fg_yellow',
            34 : 'fg_blue',
            35 : 'fg_magenta',
            36 : 'fg_cyan',
            37 : 'fg_white',
            38 : None,
            39 : None,
            40 : 'bg_black',
            41 : 'bg_red',
            42 : 'bg_green',
            43 : 'bg_yellow',
            44 : 'bg_blue',
            45 : 'bg_magenta',
            46 : 'bg_cyan',
            47 : 'bg_white',
            48 : None,
            49 : None,
        }

    def overwrite(self, num, text, tagname = None):
        """ Overwrite text to a text buffer.  Line numbering based on
            the process window line count is automatically added.
            BUT -- if multiple text buffers are going to be updated,
            always update the process buffer LAST to guarantee the
            line numbering is correct.
            Optionally, text formatting can be applied as well
        """
        if text == '':
            #debug.dprint("Notebook: overwrite() no text to overwrite... returning")
            return
        #debug.dprint("Notebook: overwrite() -- num= " + str(num) + "..." + text)
        #debug.dprint(self.current_tab)
        line_number = self.view_buffer[TAB_PROCESS].get_line_count() 
        iter = self.view_buffer[num].get_iter_at_line(line_number)
        if iter.get_chars_in_line() >= 7:
            iter.set_line_offset(7)
        else:
            debug.dprint("*** Notebook: overwrite: less than 7 chars in line... no linenumber???")
            iter.set_line_offset(0)
        end = iter.copy()
        end.forward_line()
        self.view_buffer[num].delete(iter, end)
        if tagname == None:
           self.view_buffer[num].insert_with_tags_by_name(iter, text, *self.current_tagnames)
        else:
           self.view_buffer[num].insert_with_tags_by_name(iter, text, tagname)

    def append(self, num, text, tagname = None):
        """ Append text to a text buffer.  Line numbering based on
            the process window line count is automatically added.
            BUT -- if multiple text buffers are going to be updated,
            always update the process buffer LAST to guarantee the
            line numbering is correct.
            Optionally, text formatting can be applied as well
        """
        #debug.dprint("Notebook: append() -- num= " + str(num) + "..." + text)
        #debug.dprint(self.current_tab)
        line_number = self.view_buffer[TAB_PROCESS].get_line_count() 
        iter = self.view_buffer[num].get_end_iter()
        lntext = str(line_number).zfill(6) + ' '
        if self.last_text[num].endswith('\n'):
            self.view_buffer[num].insert_with_tags_by_name(iter, lntext, 'linenumber')
        if tagname == None:
            #self.view_buffer[num].insert(iter, text)
            #debug.dprint("Notebook: append(): attempting to set text with tagnames " + str(self.current_tagnames))
            self.view_buffer[num].insert_with_tags_by_name(iter, text, *self.current_tagnames)
        else:
            self.view_buffer[num].insert_with_tags_by_name(iter, text, tagname)
        if self.auto_scroll[num] and num == self.current_tab:
            self.scroll_current_view()
        self.last_text[num] = text

    def append_all(self, text, all = False, tag = None):
        """ Append text to all buffers """
        # we need certain info in all tabs to know where
        # tab messages came from
        self.append(TAB_WARNING, text, tag)
        self.append(TAB_CAUTION, text, tag)
        self.append(TAB_INFO, text, tag)
        # NOTE: always write to the process_text buffer LAST to keep the
        # line numbers correct - see self.append above
        if all: # otherwise skip the process_text buffer
            self.append(TAB_PROCESS, text, tag)

    def parse_escape_sequence(self, sequence = "[39;49;00m"):
        """ Handles xterm escape sequences. This includes colour change requests,
        window title changes and cursor position requests
        """
        #debug.dprint("Notebook: parse_escape_sequence(): parsing '%s'" % sequence)
        if sequence.startswith("[") and sequence.endswith("m"):
            #and sequence != "[A[73G [34;01m": # <== right justify the" [OK]"
            if ";" in sequence:
                terms = sequence[1:-1].split(";")
            else:
                terms = [sequence[1:-1]]
            fg_tagname = None
            bg_tagname = None
            weight_tagname = None
            for item in terms:
                try:
                    item = int(item)
                except:
                    debug.dprint("Notebook: parse_escape_sequence(); failed to convert item '%s' to an integer" % item)
                    return False
                if 0 <= item <= 1:
                    weight_tagname = self.esc_seq_dict[item]
                elif 30 <= item <= 39:
                    fg_tagname = self.esc_seq_dict[item]
                elif 40 <= item <= 49:
                    bg_tagname = self.esc_seq_dict[item]
                else:
                    debug.dprint("Notebook: parse_escape_sequence(): ignoring term '%s'" % item)
            self.current_tagnames = []
            if fg_tagname:
                self.current_tagnames.append(fg_tagname)
            if bg_tagname:
                self.current_tagnames.append(bg_tagname)
            if weight_tagname:
                self.current_tagnames.append(weight_tagname)
            if not self.current_tagnames:
                self.current_tagnames = ['default']
            #debug.dprint("Notebook: parse_escape_sequence(): tagnames are %s" % self.current_tagnames)
            return True
        elif sequence[:3] in ["]2;", "]0;", "]1;"] and ord(sequence[-1]) == 7:
            # note: 2 = window title, 1 = icon name, 0 = window title and icon name
            sequence = sequence[3:-1]
            self.set_statusbar(sequence)
            return True
        elif sequence.startswith("k") and sequence.endswith(chr(27) + "\\"):
            sequence = sequence[1:-2]
            self.set_statusbar(sequence)
            return True
        else:
            # note: the "[A" then "[-7G" used to display "[ ok ]" on the
            # right hand side of patching lines is currently unsupported.
            debug.dprint("Notebook: parse_escape_sequence(): unsupported escape sequence '%s'" % sequence)
            return False
            
    def set_startmark( self ):
        start_iter = self.view_buffer[TAB_PROCESS].get_end_iter()
        if self.command_start:
            # move the start mark
            self.view_buffer[TAB_PROCESS].move_mark_by_name("command_start",start_iter)
        else:
            # create the mark
            self.command_start = self.view_buffer[TAB_PROCESS].create_mark( \
                "command_start",start_iter, True)
