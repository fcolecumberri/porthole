#!/usr/bin/env python

"""
    ============
    | Terminal |
    -----------------------------------------------------------
    A graphical process output viewer/filterer and emerge queue
    -----------------------------------------------------------
    Copyright (C) 2003 - 2004 Fredrik Arnerup, Brian Dolbec, 
    Daniel G. Taylor and Wm. F. Wheeler

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
    This program recognizes these run-time parameters:
        -d, --debug     Send debug messages to the screen
        -l, --local     Use the local path for data files (for cvs version)
        -v, --version   Print out the program version

    -------------------------------------------------------------------------
    To use this program as a module:
    
        from terminal import ProcessManager

        def callback():
            print "This is called when a process finishes"

        manager = ProcessManager(environment, preferences)
        manager.add_process(package_name, command_to_run, callback)
        ...
"""

# import external [system] modules
import pygtk; pygtk.require('2.0')
import gtk, gtk.glade, gobject
import signal, os, pty, threading, time, sre, portagelib
import datetime, pango, errno

if __name__ == "__main__":
    # setup our path so we can load our custom modules
    from sys import path
    path.append("/usr/lib/porthole")

# import custom modules
from utils import dprint, get_user_home_dir, SingleButtonDialog, \
                  get_treeview_selection, estimate
from version import version

# some constants for the tabs
TAB_PROCESS = 0
TAB_WARNING = 1
TAB_CAUTION = 2
TAB_INFO = 3
TAB_QUEUE = 4
# some contant strings that may be internationalized later
KILLED_STRING = "*** process killed ***\n"
TERMINATED_STRING = "*** process terminated ***\n"
TAB_LABELS = ["Process", "Warnings", "Cautions", "Information", "Emerge queue"]


class ProcessManager:
    """ Manages queued and running processes """
    def __init__(self, env = {}, prefs = None, config = None):
        """ Initialize """
        self.title = "Porthole-Terminal"
        # copy the environment and preferences
        self.env = env
        self.prefs = prefs
        self.config = config
        self.killed = 0
        self.pid = None
        self.Failed = False
        self.isPretend = False
        self.file_input = False
        # process list to store pending processes
        self.process_list = []
        # the window is not visible until a process is added
        self.window_visible = False
        # filename and serial #
        self.directory = None
        self.filename = None
        self.untitled_serial = -1
        # create the process reader
        self.reader = ProcessOutputReader(self.process_done)
        # start the reader
        self.reader.start()
        gtk.timeout_add(100, self.update)

    def show_window(self):
        """ Show the process window """
        # load the glade file
        self.wtree = gtk.glade.XML("porthole.glade", "process_window")
        # setup the callbacks
        callbacks = {"on_process_window_destroy" : self.on_process_window_destroy,
                     "on_kill" : self.kill_process,
                     "on_resume_normal" : self.resume_normal,
                     "on_resume_skip_first" : self.resume_skip_first,
                     "on_save_log" : self.do_save,
                     "on_save_log_as" : self.do_save_as,
                     "on_open_log" : self.do_open,
                     "on_copy" : self.copy_selected,
                     "on_clear" : self.clear_buffer,
                     "on_move_up" : self.move_queue_item_up,
                     "on_move_down" : self.move_queue_item_down,
                     "on_remove" : self.remove_queue_item,
                     "on_quit" : self.destroy_window}
        self.wtree.signal_autoconnect(callbacks)
        # setup some aliases for easier access
        self.window = self.wtree.get_widget("process_window")
        self.notebook = self.wtree.get_widget("notebook1")
        self.process_text = self.wtree.get_widget("process_text").get_buffer()
        self.warning_text = self.wtree.get_widget("warnings_text").get_buffer()
        self.caution_text = self.wtree.get_widget("cautions_text").get_buffer()
        self.info_text = self.wtree.get_widget("info_text").get_buffer()
        self.queue_tree = self.wtree.get_widget("queue_treeview")
        self.buffers = {TAB_LABELS[TAB_PROCESS]:self.process_text,
                        TAB_LABELS[TAB_WARNING]:self.warning_text,
                        TAB_LABELS[TAB_CAUTION]:self.caution_text,
                        TAB_LABELS[TAB_INFO]:self.info_text,
                        TAB_LABELS[TAB_QUEUE]:None}
        self.buffer_types = {TAB_LABELS[TAB_PROCESS]:"log",
                        TAB_LABELS[TAB_WARNING]:"warning",
                        TAB_LABELS[TAB_CAUTION]:"caution",
                        TAB_LABELS[TAB_INFO]:"info",
                        TAB_LABELS[TAB_QUEUE]:None}
        self.queue_menu = self.wtree.get_widget("queue1")
        self.statusbar = self.wtree.get_widget("statusbar")
        self.resume_menu = self.wtree.get_widget("resume")
        self.save_menu = self.wtree.get_widget("save1")
        self.save_as_menu = self.wtree.get_widget("save_as")
        self.open_menu = self.wtree.get_widget("open")
        self.move_up = self.wtree.get_widget("move_up1")
        self.move_down = self.wtree.get_widget("move_down1")
        self.queue_remove = self.wtree.get_widget("remove1")
        # catch clicks to the queue tree
        self.queue_tree.connect("cursor_changed", self.queue_clicked)
        # process output buffer
        self.process_buffer = ''
        # set some persistent variables for text capture
        self.catch_seq = False
        self.escape_seq = "" # to catch the escape sequence in
        # setup the queue treeview
        column = gtk.TreeViewColumn("Packages to be merged")
        pixbuf = gtk.CellRendererPixbuf()
        column.pack_start(pixbuf, expand = False)
        column.add_attribute(pixbuf, "pixbuf", 0)
        text = gtk.CellRendererText()
        column.pack_start(text, expand = True)
        column.add_attribute(text, "text", 1)
        self.queue_tree.append_column(column)
        self.queue_model = gtk.TreeStore(gtk.gdk.Pixbuf,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING)
        self.queue_tree.set_model(self.queue_model)
        # save the tab contents and remove them until we need em
        self.warning_tab = self.notebook.get_nth_page(TAB_WARNING)
        self.caution_tab = self.notebook.get_nth_page(TAB_CAUTION)
        self.info_tab = self.notebook.get_nth_page(TAB_INFO)
        self.queue_tab = self.notebook.get_nth_page(TAB_QUEUE)
        self.notebook.remove_page(TAB_QUEUE)
        self.notebook.remove_page(TAB_INFO)
        self.notebook.remove_page(TAB_CAUTION)
        self.notebook.remove_page(TAB_WARNING)
        self.warning_tab.showing = False
        self.caution_tab.showing = False
        self.info_tab.showing = False
        self.queue_tab.showing = False
        self.tablist = [TAB_LABELS[TAB_PROCESS]]
        # Create formatting tags for each textbuffers' tag table
        self.info_text.create_tag('command',\
                weight=700,\
                background='navy',\
                foreground='white')
        self.warning_text.create_tag('command',\
                weight=700,\
                background='navy',\
                foreground='white')
        self.process_text.create_tag('command',
                weight=700,\
                background='navy',\
                foreground='white')
        # All emerge lines will be bolded with light green background
        self.info_text.create_tag('emerge',\
                weight=700,\
                background='lightgreen')
        self.warning_text.create_tag('emerge',\
                weight=700,\
                background='lightgreen')
        self.process_text.create_tag('emerge',\
                weight=700,\
                background='lightgreen')
        # In process window, warnings will have medium yellow background
        self.process_text.create_tag('warning',\
                background='#ffffb0')
        self.info_text.create_tag('warning',\
                background='#ffffb0')
        # In process window info will have medium cyan background
        self.process_text.create_tag('info',\
                background='#b0ffff')
        # all line numbers will be blue & bold
        self.process_text.create_tag('linenumber',\
                foreground='blue',\
                weight=700)
        self.info_text.create_tag('linenumber',\
                foreground='blue',\
                weight=700)
        self.warning_text.create_tag('linenumber',\
                foreground='blue',\
                weight=700)
        # text mark to mark the start of the current command
        self.command_start = None
        # flag that the window is now visible
        self.window_visible = True
        if self.prefs:
            self.window.resize((self.prefs.emerge.verbose and
                                self.prefs.terminal.width_verbose or
                                self.prefs.terminal.width), 
                                self.prefs.terminal.height)
            # MUST! do this command last, or nothing else will _init__
            # after it until emerge is finished.
            # Also causes runaway recursion.
            self.window.connect("size_request", self.on_size_request)

    def on_size_request(self, window, gbox):
        """ Store new size in prefs """
        # get the width and height of the window
        width, height = window.get_size()
        # set the preferences
        if self.prefs.emerge.verbose:
            self.prefs.terminal.width_verbose = width
        else:
            self.prefs.terminal.width = width
        self.prefs.terminal.height = height

    def show_tab(self, tab):
        """ Create the label for the tab and show it """
        # this hbox will hold the icon and label
        hbox = gtk.HBox()
        icon = gtk.Image()
        # set the icon, label, tab, and position of the tab
        if tab == TAB_WARNING:
            icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)
            label, tab, pos = TAB_LABELS[TAB_WARNING], self.warning_tab, 1
        elif tab == TAB_CAUTION:
            icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)
            label, tab = TAB_LABELS[TAB_CAUTION], self.caution_tab
            # quick hack to make it always show before info & queue tabs
            pos = self.notebook.page_num(self.info_tab)
            if pos == -1:
                pos = self.notebook.page_num(self.queue_tab)
                if pos == -1:
                    pos = 2
        elif tab == TAB_INFO:
            icon.set_from_stock(gtk.STOCK_DIALOG_INFO, gtk.ICON_SIZE_MENU)
            label, tab = TAB_LABELS[TAB_INFO], self.info_tab
            pos = self.notebook.page_num(self.queue_tab)
            # set to show before queue tab
            if pos == -1: pos = 3
        elif tab == TAB_QUEUE:
            icon.set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            label, tab, pos = TAB_LABELS[TAB_QUEUE], self.queue_tab, 4
        # pack the icon and label onto the hbox
        hbox.pack_start(icon)
        hbox.pack_start(gtk.Label(label))
        hbox.show_all()
        # insert the tab
        self.notebook.insert_page(tab, hbox, pos)
        
    def add_process(self, package_name, command_string, callback):
        """ Add a process to the queue """
        # if it's already in the queue, don't add it!
        for data in self.process_list:
            if package_name == data[0]: return
        # show the window if it isn't yet
        if not self.window_visible:
            self.show_window()
        # add to the queue
        iter = self.queue_model.insert_before(None, None)
        self.queue_model.set_value(iter, 0, None)
        self.queue_model.set_value(iter, 1, str(package_name))
        self.queue_model.set_value(iter, 2, str(command_string))
        # add to our process list
        self.process_list.append((package_name, command_string,
                                                iter, callback))

        if len(self.process_list) == 2:
            # if this is the 2nd process in the list
            # show the queue tab!
            if not self.queue_tab.showing:
                self.show_tab(TAB_QUEUE)
                self.queue_menu.set_sensitive(gtk.TRUE)
                self.queue_tab.showing = True
        # if no process is running, let's start this one!
        if not self.reader.process_running:
            self._run(command_string, iter)

    def _run(self, command_string, iter = None):
        """ Run a given command string """
        # we can't be killed anymore
        self.killed = 0
        self.warning_count = 0
        self.Failed = False
        self.isPretend = command_string.find('--pretend') > -1
        start_iter = self.process_text.get_end_iter()
        if self.command_start:
            # move the start mark
            self.process_text.move_mark_by_name("command_start",start_iter)
        else:
            # create the mark
            self.command_start = self.process_text.create_mark( \
                "command_start",start_iter, gtk.TRUE)
        # set the resume buttons to not be sensitive
        self.resume_menu.set_sensitive(gtk.FALSE)
        self.save_menu.set_sensitive(gtk.FALSE)
        self.save_as_menu.set_sensitive(gtk.FALSE)
        self.open_menu.set_sensitive(gtk.FALSE)
        if iter:
            self.queue_model.set_value(iter, 0, 
                             self.render_icon(gtk.STOCK_EXECUTE))
        # set process_running so the reader thread reads it's output
        self.reader.process_running = True
        # show a message that the process is starting
        self.append_all("*** " + command_string + " ***\n", True, 'command')
        self.set_statusbar("*** " + command_string + " ***")
        # pty.fork() creates a new process group
        self.pid, self.reader.fd = pty.fork()
        if self.pid == pty.CHILD:  # child
            try:
                # run the commandbuffer.tag_table.lookup(tagname)
                shell = "/bin/sh"
                os.execve(shell, [shell, '-c', command_string],
                          self.env)
                
            except Exception, e:
                # print out the exception
                dprint("Error in child" + e)
                print "Error in child:"
                print e
                os._exit(1)

    def destroy_window(self, widget):
        """ Destroy the window when the close button is pressed """
        self.window.destroy()

    def on_process_window_destroy(self, widget, data = None):
        """Window was closed"""
        # kill any running processes
        self.kill()
        # make sure to reset the process list
        self.process_list = []
        # the window is no longer showing
        self.window_visible = False
        if __name__ == "__main__":
            # if running standalone, quit
            gtk.main_quit()

    def kill(self):
        """Kill process."""
        # If started and still running
        if self.pid and not self.killed:
            try:
                # make sure the thread notices
                os.close(self.reader.fd)
                # negative pid kills process group
                os.kill(-self.pid, signal.SIGKILL)
            except OSError:
                pass
            self.killed = 1
            if self.queue_tab.showing:
                # update the queue tree
                self.queue_clicked(self.queue_tree)

    def append(self, buffer, text, tagname = None):
        """ Append text to a text buffer.  Line numbering based on
            the process window line count is automatically added.
            BUT -- if multiple text buffers are going to be updated,
            always update the process buffer LAST to guarantee the
            line numbering is correct.
            Optionally, text formatting can be applied as well
        """
        line_number = self.process_text.get_line_count() 
        iter = buffer.get_end_iter()
        lntext = '000000' + str(line_number) + ' '
        buffer.insert_with_tags_by_name(iter, lntext[-7:] , 'linenumber')
        if tagname == None:
           buffer.insert(iter, text)
        else:
           buffer.insert_with_tags_by_name(iter, text, tagname)

    def append_all(self, text, all = False, tag = None):
        """ Append text to all buffers """
        # we need certain info in all tabs to know where
        # tab messages came from
        self.append(self.warning_text, text, tag)
        #self.append(self.caution_text, text, tag)
        self.append(self.info_text, text, tag)
        # NOTE: always write to the process_text buffer LAST to keep the
        # line numbers correct - see self.append above
        if all: # otherwise skip the process_text buffer
            self.append(self.process_text, text, tag)


    def update(self):
        """ Add text to the buffer """
        # stores line of text in buffer
        # if the string is locked, we'll get it on the next round
        cr_flag = False   # Carriage Return flag
        if self.reader.string_locked:
            return gtk.TRUE
        # lock the string
        self.reader.string_locked = True
        for char in self.reader.string:
            if char:
                # if we find a CR without a LF, clear the buffer
                if cr_flag:
                   if char != '\n':
                      self.process_buffer = ''
                   cr_flag = False
                # catch portage escape sequence NOCOLOR bugs
                if ord(char) == 27 or self.catch_seq:
                        self.catch_seq = True
                        if ord(char) != 27:
                            self.escape_seq += char
                        if char == 'm':
                            self.catch_seq = False
                            #dprint('escape_seq='+escape_seq)
                            self.escape_seq = ""
                elif char == '\b' : # backspace
                    self.process_buffer = self.process_buffer[:-1]
                elif ord(char) == 13:  # carriage return
                    cr_flag = True
                elif 32 <= ord(char) <= 127 or char == '\n': # no unprintable
                    self.process_buffer += char
                    if char == '\n': # newline
                        tag = None
                        
                        if self.config.isEmerge(self.process_buffer):
                            self.set_statusbar(self.process_buffer[:-1])
                            # add the pkg info to all other tabs to identify fom what
                            # pkg messages came from but no need to show it if it isn't
                            tag = 'emerge'
                            self.append(self.info_text, self.process_buffer, tag)
                            self.append(self.warning_text, self.process_buffer, tag)
                            if not self.file_input:
                                self.set_file_name(self.process_buffer)

                        elif self.config.isInfo(self.process_buffer):
                            # info string has been found, show info tab if needed
                            if not self.info_tab.showing:
                                self.show_tab(TAB_INFO)
                                self.info_tab.showing = True
                                self.info_text.set_modified(gtk.TRUE)
                            # insert the line into the info text buffer
                            tag = 'info'
                            self.append(self.info_text, self.process_buffer)
                            # Check for fatal error
                            if self.config.isError(self.process_buffer):
                                self.Failed = True

                        elif self.config.isWarning(self.process_buffer):
                            # warning string has been found, show info tab if needed
                            if not self.warning_tab.showing:
                                self.show_tab(TAB_WARNING)
                                self.warning_tab.showing = True
                                self.warning_text.set_modified(gtk.TRUE)
                            # insert the line into the info text buffer
                            tag = 'warning'
                            self.append(self.warning_text, self.process_buffer)
                            self.warning_count += 1

                        elif self.config.isCaution(self.process_buffer):
                            # warning string has been found, show info tab if needed
                            if not self.caution_tab.showing:
                                self.show_tab(TAB_CAUTION)
                                self.caution_tab.showing = True
                                self.caution_text.set_modified(gtk.TRUE)
                            # insert the line into the info text buffer
                            tag = None # yet
                            self.append(self.caution_text, self.process_buffer)
                            self.caution_count += 1

                        self.append(self.process_text, self.process_buffer, tag)
                        self.process_buffer = ''  # reset buffer
                elif ord(char) == 13: # carriage return?
                    pass
        self.reader.string = ""
        if self.file_input:
            self.process_text.set_modified(gtk.FALSE)
            if self.warning_count != 0:
                self.append(self.info_text, "*** Total warnings count for merge = %d \n"\
                            %self.warning_count, 'warning')
            self.set_statusbar("*** Log loading complete : %s" % self.filename)
            self.file_input = False
        # unlock the string
        self.reader.string_locked = False
        return gtk.TRUE

    def set_file_name(self, line):
        """extracts the ebuild name and assigns it to self.filename"""
        x = line.split("/")
        y = x[1].split(" ")
        name = y[0]
        self.filename = name + "." + self.buffer_types[TAB_LABELS[TAB_PROCESS]]
        dprint("new ebuild detected, new filename: " + self.filename)
        return

    def set_statusbar(self, string):
        """Update the statusbar without having to use push and pop."""
        self.statusbar.pop(0)
        self.statusbar.push(0, string)

    def process_done(self):
        """ Remove the finished process from the queue, and
        start the next one if there are any more to be run"""
        # if the last process was killed, stop until the user does something
        if self.killed:
            # display message that process has been killed
            self.append_all(KILLED_STRING,True)
            self.set_statusbar(KILLED_STRING[:-1])
            return
            
        # If the user did an emerge --pretend, we print out
        # estimated build times on the output window
        if self.isPretend:
            self.estimate_build_time()
        if self.warning_count != 0:
            self.append(self.info_text, "*** Total warnings count for merge = %d \n"\
                        %self.warning_count, 'warning')
        # display message that process finished
        self.append_all(TERMINATED_STRING,True)
        self.set_statusbar(TERMINATED_STRING[:-1])
        # try to get a callback
        callback = self.process_list[0][3]
        # set queue icon to done
        iter = self.process_list[0][2]
        # set icon according to success or failure
        if self.Failed:
            self.queue_model.set_value(iter, 0, self.render_icon(gtk.STOCK_CANCEL))
        else:
            self.queue_model.set_value(iter, 0, self.render_icon(gtk.STOCK_APPLY))
        # remove process from list
        self.process_list = self.process_list[1:]
        # check for pending processes, and run them
        if len(self.process_list):
            dprint("TERMINAL: There are pending processes, running now... [" + \
                    self.process_list[0][0] + "]")
            self._run(self.process_list[0][1], self.process_list[0][2])
        else: # re-activate the open/save menu items
            self.save_menu.set_sensitive(gtk.TRUE)
            self.save_as_menu.set_sensitive(gtk.TRUE)
            self.open_menu.set_sensitive(gtk.TRUE)
        # if there is a callback set, call it
        if callback:
            callback()
        if self.queue_tab.showing:
            # update the queue tree
            self.queue_clicked(self.queue_tree)

    def render_icon(self, icon):
        """ Render an icon for the queue tree """
        return self.queue_tree.render_icon(icon,
                    size = gtk.ICON_SIZE_MENU, detail = None)

    def kill_process(self, widget):
        """ Kill currently running process """
        if not self.reader.process_running:
            dprint("TERMINAL: No running process to kill!")
            return
        self.kill()
        # set the queue icon to killed
        iter = self.process_list[0][2]
        self.queue_model.set_value(iter, 0, self.render_icon(gtk.STOCK_CANCEL))
        # set the resume buttons to sensitive
        self.resume_menu.set_sensitive(gtk.TRUE)

    def resume_normal(self, widget):
        """ Resume killed process """
        # pass the normal command along with --resume
        name, command, iter, callback = self.process_list[0]
        self._run(command + " --resume", iter)

    def resume_skip_first(self, widget):
        """ Resume killed process, skipping first package """
        # pass the normal command along with --resume --skipfirst
        name, command, iter, callback = self.process_list[0]
        self._run(command + " --resume --skipfirst", iter)

    def copy_selected(self, widget):
        """ Copy selected text to clipboard """
        pass

    def clear_buffer(self, widget):
        """ Clear the text buffer """
        self.process_text.set_text('')
        self.warning_text.set_text('')
        self.caution_text.set_text('')
        self.info_text.set_text('')
        self.process_text.set_modified(gtk.FALSE)
        self.warning_text.set_modified(gtk.FALSE)
        self.caution_text.set_modified(gtk.FALSE)
        self.info_text.set_modified(gtk.FALSE)
        self.filename = None

    def queue_items_switch(self, direction):
        """ Switch two adjacent queue items;
            direction is either 1 [down] or -1 [up] """
        dprint("TERMINAL: Switching queue items.")
        # get the selected iter
        iter = get_treeview_selection(self.queue_tree)
        # get its path
        path = self.queue_model.get_path(iter)[0]
        # only move up if it's not the first entry,
        # only move down if it's not the last entry
        if (not direction and path > 0) or \
           (direction and path < len(self.queue_model)):
            # get the selected value
            selected = self.queue_model[path]
            # get the adjacent value
            prev = self.queue_model[path + direction]
            # store selected temporarily so it's not overwritten
            temp = (selected[0], selected[1], selected[2])
            # switch sides and make sure the original is still selected
            self.queue_model[path] = prev
            self.queue_model[path + direction] = temp
            self.queue_tree.get_selection().select_path(path + direction)
            # switch the process list entries
            # basically similar to above, except that the iters are _not_ switched
            for pos in range(len(self.process_list)):
                if self.process_list[pos][0] == temp[1] and pos > 0:
                    sel = self.process_list[pos][0], self.process_list[pos][1],\
                          self.process_list[pos + direction][2], \
                          self.process_list[pos][3]
                    prev = self.process_list[pos + direction][0],\
                           self.process_list[pos + direction][1],\
                           self.process_list[pos][2],\
                           self.process_list[pos + direction][3]
                    self.process_list[pos] = prev
                    self.process_list[pos + direction] = sel
                    break
        else:
            dprint("TERMINAL: cannot move first or last item")
        self.queue_clicked(self.queue_tree)

    def move_queue_item_up(self, widget):
        """ Move selected queue item up in the queue """
        self.queue_items_switch(-1)

    def move_queue_item_down(self, widget):
        """ Move selected queue item down in the queue """
        self.queue_items_switch(1)

    def remove_queue_item(self, widget):
        """ Remove the selected item from the queue """
        # get the selected iter
        iter = get_treeview_selection(self.queue_tree)
        # find if this item is still in our process list
        name = get_treeview_selection(self.queue_tree, 1)
        for pos in range(len(self.process_list)):
            if name == self.process_list[pos][0]:
                # remove the item from the list
                self.process_list = self.process_list[:pos] + \
                                    self.process_list[pos + 1:]
                break
        self.queue_model.remove(iter)

    def estimate_build_time(self):
        """Estimates build times based on emerge --pretend output"""
        start_iter = self.process_text.get_iter_at_mark(self.command_start)
        output = self.process_text.get_text(start_iter,
                                 self.process_text.get_end_iter(), gtk.FALSE)
        package_list = []
        total = datetime.timedelta()        
        for line in output.split("\n"):
            if self.config.ebuild_re.match(line):
                tokens = line.split(']')
                tokens = tokens[1].split()
                tmp_name = portagelib.get_name(tokens[0])
                name = ""
                # We want to get rid of the version number in the package name
                # because if a user is upgrading from, for instance, mozilla 1.4 to
                # 1.5, there's a good chance the build times will be pretty close.
                # So, we want to match only on the name
                for j in range(0, len(tmp_name)):
                    if tmp_name[j] == "-" and tmp_name[j+1].isdigit():
                        break
                    else:
                        name += tmp_name[j]        
                package_list.append(name)
        if len(package_list) > 0:  
            for package in package_list:
                try:
                    curr_estimate = estimate(package)
                except:
                    return None
                if curr_estimate != None:
                    total += curr_estimate
                else:
                    self.append(self.process_text,
                            "*** Unfortunately, you don't have enough " +
                            "logged information about the listed packages, " +
                            "so I can't calculate estimated build times " +
                            "accuratelly.\n", 'emerge')
                    self.append(self.process_text, "\n")
                    return None
            self.append(self.process_text,
                        "*** Based on the build history of these packages " +
                        "on your system, I can estimate that emerging them " +
                        "usually takes, on average, " + 
                        "%d days, %d hrs, %d mins, and %d secs.\n" %
                        (total.seconds // (24 * 3600),\
                         (total.seconds % (24 * 3600)) // 3600,\
                         ((total.seconds % (24 * 3600))  % 3600) //  60,\
                         ((total.seconds % (24 * 3600))  % 3600) %  60), 'emerge')
            self.append(self.process_text, "\n")
            self.append(self.process_text,
                        "*** Note: If you have a lot of programs running on " +
                        "your system while porthole is emerging packages, " +
                        "or if you have changed your hardware since the " +
                        "last time you built some of these packages, the " +
                        "estimates I calculate may be inaccurate.\n", 'warning')
            self.append(self.process_text, "\n")

    def queue_clicked(self, widget):
        """Handle clicks to the queue treeview"""
        # get the selected iter
        iter = get_treeview_selection(self.queue_tree)
        # get its path
        try:
            path = self.queue_model.get_path(iter)[0]
        except:
            dprint("TERMINAL: Couldn't get queue view treeiter path,\
                    there is probably nothing selected.")
            return
        # if the item is not in the process list
        # don't make the controls sensitive and return
        name = get_treeview_selection(self.queue_tree, 1)
        in_list = 0
        for pos in range(len(self.process_list)):
            if self.process_list[pos][0] == name:
                # set the position in the list (+1 so it's not 0)
                in_list = pos + 1
        if not in_list or in_list == 1 or in_list == len(self.process_list):
            self.move_up.set_sensitive(gtk.FALSE)
            self.move_down.set_sensitive(gtk.FALSE)
            if not self.killed and in_list == 1:
                self.queue_remove.set_sensitive(gtk.FALSE)
            else:
                self.queue_remove.set_sensitive(gtk.TRUE)
            return
        # if we reach here it's still in the process list
        # activate the delete item
        self.queue_remove.set_sensitive(gtk.TRUE)
        # set the correct directions sensitive
        # shouldn't be able to move the top item up, etc...
        if in_list == 2 or path == 0:
            self.move_up.set_sensitive(gtk.FALSE)
            self.move_down.set_sensitive(gtk.TRUE)
        elif path == len(self.queue_model) - 1:
            self.move_up.set_sensitive(gtk.TRUE)
            self.move_down.set_sensitive(gtk.FALSE)
        else:
            # enable moving the item
            self.move_up.set_sensitive(gtk.TRUE)
            self.move_down.set_sensitive(gtk.TRUE)

    def set_save_buffer(self):
        """determines the notebook tab open and returns the visible buffer"""
        dprint("entering set_save_buffer")
        self.tabs_showing = 0
        tabs = 0
        self.tablist = [TAB_LABELS[TAB_PROCESS]]
        for tab in [self.warning_tab.showing, self.caution_tab.showing,
                    self.info_tab.showing, self.queue_tab.showing]:
            tabs += 1
            if tab:
                self.tabs_showing += 1
                self.tablist += [TAB_LABELS[tabs]]
        dprint(self.tablist)
        page = self.notebook.get_current_page()
        self.buffer_name = self.tablist[page]
        self.buffer_to_save = self.buffers[self.buffer_name]
        self.buffer_type = self.buffer_types[self.buffer_name]
        dprint("set_save_buffer: " + self.buffer_name + " type: " + self.buffer_type)
        return (self.buffer_name != None)

    def open_ok_func(self, filename):
        """callback function from file selector"""
        dprint("entering callback open_ok_func")
        if not self.fill_buffer(filename):
            self.set_statusbar("*** Unknown File Loading error")
            return gtk.FALSE
        else:
            self.filename = filename
            self.set_statusbar("*** File Loaded... Processing..") 
            return gtk.TRUE;

    def do_open(self, widget):
        """opens the file selctor for file to open"""
        dprint("entering do_open")
        if not self.directory:
            self.set_directory()
        FileSel("Porthole-Terminal: Open log File").run(self.window,
                                                        None,
                                                        self.open_ok_func)

    def do_save_as(self, widget):
        """determine buffer to save as and saves it"""
        dprint("entering do_save_as")
        if not self.directory:
            self.set_directory()
        if self.set_save_buffer():
            result = self.check_buffer_saved(self.buffer_to_save, False)
        else:
            dprint("Error: buffer is already saved")

    def do_save(self, widget):
        """determine buffer to save and proceed"""
        dprint("entering do_save")
        if not self.directory:
            self.set_directory()
        if not self.filename:
            self.do_save_as(widget)
        else:
            if self.set_save_buffer():
                result = self.check_buffer_saved(self.buffer_to_save, True)
            else:
                dprint("set_save_buffer error")

    def save_as_buffer(self):
        dprint("entering save_as_buffer")
        return FileSel("Porthole-Terminal: Save File").run(self.window,
                                                           self.filename,
                                                           self.save_as_ok_func)

    def save_as_ok_func(self, filename):
        """file selector callback function"""
        dprint("entering save_as_ok_func")
        old_filename = self.filename

        if (not self.filename or filename != self.filename):
            if os.path.exists(filename):
                err = "Ovewrite existing file '%s'?"  % filename
                dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                           gtk.MESSAGE_QUESTION,
                                           gtk.BUTTONS_YES_NO, err);
                result = dialog.run()
                dialog.destroy()
                if result != gtk.RESPONSE_YES:
                    return gtk.FALSE

        self.filename = filename

        if self.save_buffer():
            return gtk.TRUE
        else:
            self.filename = old_filename
            return gtk.FALSE

    def set_directory(self):
        """sets the starting directory for file selection"""
        if not self.directory:
            # no directory was specified, so we are making one up
            dprint("LOG: directory not specified, saving to ~/.porthole/logs")
            self.directory = get_user_home_dir()
            if os.access(self.directory + "/.porthole", os.F_OK):
                if not os.access(self.directory + "/.porthole/logs", os.F_OK):
                    dprint("LOG: Creating logs directory in " + self.directory +
                           "/.porthole/logs")
                    os.mkdir(self.directory + "/.porthole/logs")
                self.directory += "/.porthole/logs/"
                os.chdir(self.directory)
 
    def pretty_name(self):
        """pre-assigns generic filename & serial #"""
        dprint("entering pretty_name")
        # check if filename set and set the extension to the correct buffer type 
        if self.filename and self.filename[:7] != "Untitled":
            filename = os.path.basename(self.filename)
            filename = filename.split(".")
            newname = filename[0]
            for x in filename[1:-1]:
                newname += ("." + x)
            self.filename = newname + "." + self.buffer_type
            dprint(self.filename)
            return self.filename
        else: # Untitlted filename
            if not self.directory: # just in case it is not set
                self.set_directory()
            if self.untitled_serial == -1:
                self.untitled_serial = 1
            else:
                self.untitled_serial += 1
            filename = ("Untitled-%d.%s" % (self.untitled_serial, self.buffer_type))
            while os.path.exists(filename): # find the next available filename
                self.untitled_serial += 1
                filename = ("Untitled-%d.%s" % (self.untitled_serial, self.buffer_type))
            return filename

    def fill_buffer(self, filename):
        """loads a file into the reader.string"""
        dprint("entering fill_buffer")
        self.clear_buffer(None)
        self.warning_count = 0
        self.set_statusbar("*** Loading File : %s" % self.filename)
        try:
            f = open(filename, "r")
        except IOError, (errnum, errmsg):
            err = "Cannot open file '%s': %s" % (filename, errmsg)
            dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                       gtk.MESSAGE_INFO,
                                       gtk.BUTTONS_OK, err);
            result = dialog.run()
            dialog.destroy()
            return gtk.FALSE

        if not self.reader.string_locked:
            self.file_input = True
            self.reader.string_locked = True
            self.reader.string = f.read()
            f.close()
            self.reader.string_locked = False
            #self.set_statusbar("*** Log loading complete : %s" % self.filename)
            dprint("leaving fill_buffer")
            return gtk.TRUE
        else:
            err = "Error: 'reader.string' currently locked, ensure no process is running"
            dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                       gtk.MESSAGE_INFO,
                                       gtk.BUTTONS_OK, err);
            result = dialog.run()
            dialog.destroy()
            return gtk.FALSE
            

    def save_buffer(self):
        """save the contens of the buffer"""
        dprint("entering save_buffer")
        result = gtk.FALSE
        have_backup = gtk.FALSE
        if not self.filename:
            return gtk.FALSE

        bak_filename = self.filename + "~"
        try:
            os.rename(self.filename, bak_filename)
        except (OSError, IOError), (errnum, errmsg):
            if errnum != errno.ENOENT:
                err = "Cannot back up '%s' to '%s': %s" % (self.filename,
                                                           bak_filename,
                                                           errmsg)
                dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                           gtk.MESSAGE_INFO,
                                           gtk.BUTTONS_OK, err);
                dialog.run()
                dialog.destroy()
                return gtk.FALSE

        have_backup = gtk.TRUE
        self.set_statusbar("*** saving file: %s" % self.filename)
        try:
            file = open(self.filename, "w")
            # if buffer is "Process" strip line numbers
            if self.buffer_name == TAB_LABELS[TAB_PROCESS]:
                start = self.buffer_to_save.get_start_iter()
                while not start.is_end():
                    end = start.copy(); end.forward_line()
                    chars = self.buffer_to_save.get_text(start, end, gtk.FALSE)
                    file.write(chars[7:])
                    chars = ""
                    start.forward_line()
                    
            else: # save the entire buffer
                start, end = self.buffer_to_save.get_bounds()
                chars = self.buffer_to_save.get_text(start, end, gtk.FALSE)
                file.write(chars)

            file.close()
            self.buffer_to_save.set_modified(gtk.FALSE)
            result = gtk.TRUE
        except IOError, (errnum, errmsg):
            err = "Error writing to '%s': %s" % (self.filename, errmsg)
            dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                       gtk.MESSAGE_INFO,
                                       gtk.BUTTONS_OK, err);
            dialog.run()
            dialog.destroy()

        if not result and have_backup:
            try:
                os.rename(bak_filename, self.filename)
            except OSError, (errnum, errmsg):
                err = "Can't restore backup file '%s' to '%s': %s\nBackup left as '%s'" % (
                    self.filename, bak_filename, errmsg, bak_filename)
                dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                           gtk.MESSAGE_INFO,
                                           gtk.BUTTONS_OK, err);
                dialog.run()
                dialog.destroy()

        self.set_statusbar("*** File saved : %s" % self.filename)
        dprint("buffer saved, exiting")
        return result

    def check_buffer_saved(self, buffer, save = False):
        """checks if buffer has been modified before saving again"""
        dprint("entering check_buffer_saved")
        self.filename = self.pretty_name()
        if buffer.get_modified():
            if save:
                msg = "Save log to '%s'?" % self.filename
                dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                           gtk.MESSAGE_QUESTION,
                                           gtk.BUTTONS_YES_NO, msg);
                dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
                result = dialog.run()
                dialog.destroy()
                if result == gtk.RESPONSE_YES:
                    if self.filename:
                        return self.save_buffer()
                    return self.save_as_buffer()
                elif result == gtk.RESPONSE_NO:
                    return self.save_as_buffer()
                else:
                    return gtk.FALSE
            else: # save_as
                    return self.save_as_buffer()
        else:
            msg = "Buffer already saved &/or has not been modified: Proceed?"
            dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                       gtk.MESSAGE_QUESTION,
                                       gtk.BUTTONS_YES_NO, msg);
            dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            result = dialog.run()
            dialog.destroy()
            if result == gtk.RESPONSE_YES:
                return self.save_as_buffer()
            elif result == gtk.RESPONSE_NO:
                return gtk.FALSE
            else:
                return gtk.FALSE

class FileSel(gtk.FileSelection):
    def __init__(self, title):
        gtk.FileSelection.__init__(self, title)
        self.result = gtk.FALSE

    def ok_cb(self, button):
        self.hide()
        if self.ok_func(self.get_filename()):
            self.destroy()
            self.result = gtk.TRUE
        else:
            self.show()

    def run(self, parent, start_file, func):
        if start_file:
            self.set_filename(start_file)

        self.ok_func = func
        self.ok_button.connect("clicked", self.ok_cb)
        self.cancel_button.connect("clicked", lambda x: self.destroy())
        self.connect("destroy", lambda x: gtk.main_quit())
        self.set_modal(gtk.TRUE)
        self.show()
        gtk.main()
        return self.result


class ProcessOutputReader(threading.Thread):
    """ Reads output from processes """
    def __init__(self, finished_callback):
        """ Initialize """
        threading.Thread.__init__(self)
        # set callback
        self.finished_callback = finished_callback
        self.setDaemon(1)  # quit even if this thread is still running
        self.process_running = False
        # initialize only, self.fd set by in ProcessManager._run()
        self.fd = None
        # string to store input from process
        self.string = ""
        # lock to prevent loosing characters from simultaneous accesses
        self.string_locked = False

    def run(self):
        """ Watch for process output """
        while True:
            if self.process_running:
                # get the output and pass it to self.callback()
                try:
                    char = os.read(self.fd, 1)
                except OSError:
                    # maybe the process died?
                    char = None
                if char:
                    # if the string is currently being accessed
                    while(self.string_locked):
                        # wait 50 ms and check again
                        time.sleep(0.05)
                    # lock the string
                    self.string_locked = True
                    # add the character to the string
                    self.string += char
                    # unlock the string
                    self.string_locked = False
                else:
                    # clean up, process is terminated
                    self.process_running = False
                    while self.string != "":
                        # wait for update_callback to finish
                        time.sleep(.5)
                    gtk.threads_enter()
                    self.finished_callback()
                    gtk.threads_leave()
            else:
                # sleep for .5 seconds before we check again
                time.sleep(.5)


if __name__ == "__main__":

    def callback():
        """ Print a message to display that callbacks are working"""
        dprint("TERMINAL: Callback caught...")
    
    DATA_PATH = "/usr/share/porthole/"

    from sys import argv, exit, stderr
    from getopt import getopt, GetoptError
    import utils

    try:
        opts, args = getopt(argv[1:], "lvd", ["local", "version", "debug"])
    except GetoptError, e:
        print >>stderr, e.msg
        exit(1)

    for opt, arg in opts:
        if opt in ('-l', "--local"):
            # running a local version (i.e. not installed in /usr/*)
            DATA_PATH = ""
        elif opt in ('-v', "--version"):
            # print version info
            print "Porthole-Terminal " + version
            exit(0)
        elif opt in ('-d', "--debug"):
            utils.debug = True
            utils.dprint("Debug printing is enabled")
    # change dir to your data path
    if DATA_PATH:
        from os import chdir
        chdir(DATA_PATH)
    # make sure gtk lets threads run
    gtk.threads_init()
    # setup our app icon
    myicon = gtk.gdk.pixbuf_new_from_file("pixmaps/porthole-icon.png")
    gtk.window_set_default_icon_list(myicon)
    # load prefs
    prefs = utils.PortholePreferences()
    env = utils.environment()
    # to test the above classes when run standalone
    test = ProcessManager(env, prefs)
    test.title = "Porthole-Terminal"
    test.add_process("kde (-vp)", "emerge -vp kde", callback)
    # un-comment the next line to get the queue to show up
    test.add_process("gnome (-vp)", "emerge -vp gnome", callback)
    test.add_process("gtk+ (-vp)", "emerge -vp gtk+", callback)
    test.add_process("bzip2 (-v)", "emerge -v bzip2", callback)
    # start the program loop
    gtk.mainloop()
    # save the prefs to disk for next time
    prefs.save()
