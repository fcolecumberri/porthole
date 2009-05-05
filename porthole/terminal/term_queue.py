#!/usr/bin/env python

"""
    ============
    | Terminal Queue |
    -----------------------------------------------------------
    A graphical process queue
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
    
        from term_queue import TerminalQueue

        def callback():
            print "This is called when a process finishes"

        my_queue = TerminalQueue(glade_tree, terminal_notebook)
        my_queue.add_process(package_name, command_to_run, callback)
        ...
    -------------------------------------------------------------------------
    References & Notes
    
    1. Pygtk2 refs & tutorials - http://www.pygtk.org
    2. GTK2 text tags can use named colors (see /usr/X11R6/lib/X11/rgb.txt)
        or standard internet rgb values (e.g. #02FF80)
    
"""

# import external [system] modules
import pygtk; pygtk.require('2.0')
import gtk, gtk.glade, gobject
import pango
from types import *
#import signal, os, pty, threading, time, sre, portagelib
#import datetime, pango, errno

#from porthole.utils import Dispatcher
#from porthole.readers import ProcessOutputReader
from porthole.utils.utils import get_treeview_selection
from porthole.utils import debug
from porthole.terminal.constants import *
from porthole.dialogs.simple import SingleButtonDialog

FUNCTIONTYPES = [FunctionType, MethodType, BuiltinFunctionType, BuiltinMethodType]

class QueueModel(gtk.ListStore):
    def __init__(self):
        gtk.ListStore.__init__(self, gtk.gdk.Pixbuf,            # hold the status icon
                                        gobject.TYPE_STRING,         # package name/ command name
                                        gobject.TYPE_STRING,         # command
                                        gobject.TYPE_INT,                # entry id
                                        gobject.TYPE_STRING,        # sender
                                        gobject.TYPE_BOOLEAN,    # killed
                                        gobject.TYPE_PYOBJECT,   # callback function
                                        gobject.TYPE_BOOLEAN,    # completed
                                        gobject.TYPE_INT                # killed_id
                                        )
        self.column = {'icon': 0,
                                'name':  1,
                                'command': 2,
                                'id': 3,
                                'sender': 4,
                                'killed': 5,
                                'callback': 6,
                                'completed': 7,
                                'killed_id': 8
                                }

    def copy(self, path,  mytype = 'tuple'):
        """perform a data copy
            return a tuple of the data in the correct order
        """
        #debug.dprint("QueueModel: copy(); mytype = " + mytype)
        iter = self.get_iter(path)
        if mytype == 'tuple':
            myval = []
            for i in self.column:
                myval.append(self.get_value(iter, self.column[i]))
            return tuple(myval)
        elif mytype == 'dict':
            myval = {}
            for i in self.column:
                myval[i] = self.get_value(iter, self.column[i])
            return myval

    def get_column_list(self):
        """retrun a dictionary of the column names and position in the data structure
        """
        return self.column.copy()

    def set_data(self, iter, data):
        if iter:
            if type(data) is DictType:
                debug.dprint("QueueModel: set_data(); DictType data['icon'] type = " + str(type(data['icon'])))
                for i in data:
                    self.set_value(iter,self.column[i], data[i])
            elif type(data) is ListType:
                debug.dprint("QueueModel: set_data(); ListType data = " + str(data))
                #if type(data[self.column['icon']]) is NoneType:
                self.set_value(iter, self.column['icon'], data[self.column['icon']])
                self.set_value(iter, self.column['name'], data[self.column['name']])
                self.set_value(iter, self.column['command'], data[self.column['command']])
                self.set_value(iter, self.column['id'], data[self.column['id']])
                self.set_value(iter, self.column['sender'], data[self.column['sender']])
                self.set_value(iter, self.column['callback'], data[self.column['callback']])
                self.set_value(iter, self.column['completed'], data[self.column['completed']])
            return True
        else:
            return False


class ProcessItem:
    def __init__(self, name, command, process_id, callback = None, sender = 'Non-DBus'):
        """Structure of a process list item"""
        ## old process item structure [package_name, command_string, iter, callback, self.process_id]
        self.name = name
        self.command = command
        self.callback = callback
        self.sender = sender
        self.killed = False
        # id number for storing in the queue
        self.process_id = process_id
        self.killed_id = None
        self.completed = False

class TerminalQueue:
    """A QUEUE queue"""
    def __init__(self, run_function = None, reader = None, wtree = None, term = None, set_resume = None):
        self._run = run_function
        self.reader = reader
        self.wtree = wtree
        self.term = term
        self.set_resume = set_resume
        # initialize the model
        self.queue_model = QueueModel()
        self.queue_paused = False
        self.process_id = 0
        self.next_id = 1
        self.process_iter = None
        self.last_run_iter = None
        self.task_completed = False
        self.killed_id = None
        self.window = wtree.get_widget("process_window")
        self.queue_tree = wtree.get_widget("queue_treeview")
        self.queue_menu = wtree.get_widget("queue1")
        self.resume_menu = self.wtree.get_widget("resume")
        self.skip_first_menu = self.wtree.get_widget("skip_first1")
        self.skip_queue_menu = self.wtree.get_widget("skip_queue")
        self.move_up = self.wtree.get_widget("move_up1")
        self.move_down = self.wtree.get_widget("move_down1")
        self.queue_remove = self.wtree.get_widget("remove1")
        self.save_menu = self.wtree.get_widget("save1")
        self.save_as_menu = self.wtree.get_widget("save_as")
        self.open_menu = self.wtree.get_widget("open")
        self.play_btn = self.wtree.get_widget("play_queue_button")
        self.play_menu = self.wtree.get_widget("resume_queue")
        self.pause_btn = self.wtree.get_widget("pause_button")
        self.pause_menu = self.wtree.get_widget("pause")
        #debug.dprint("TERM_QUEUE: Attempting to change the pause, paly button image colors")
        """ Set up different colors for the pause & play buttons depending on it's state
            gtk.STATE_NORMAL	State during normal operation.
            gtk.STATE_ACTIVE	State of a currently active widget, such as a depressed button.
            gtk.STATE_PRELIGHT	State indicating that the mouse pointer is over the widget and the widget will respond to mouse clicks.
            gtk.STATE_SELECTED	State of a selected item, such the selected row in a list.
            gtk.STATE_INSENSITIVE	State indicating that the widget is unresponsive to user actions.
        """
        self.pause_btn.modify_fg(gtk.STATE_INSENSITIVE, gtk.gdk.color_parse("#962A1C"))
        self.pause_btn.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#DA311B"))
        self.pause_btn.modify_fg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse("#F65540"))
        self.play_btn.modify_fg(gtk.STATE_INSENSITIVE, gtk.gdk.color_parse("#3C6E38"))
        self.play_btn.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#4EBA44"))
        self.play_btn.modify_fg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse("#58F64A"))
        # catch clicks to the queue tree
        self.queue_tree.connect("cursor-changed", self.clicked)
        # setup the queue treeview
        column = gtk.TreeViewColumn(_("id"))
        text = gtk.CellRendererText()
        column.pack_start(text, expand = True)
        column.add_attribute(text, "text",self.queue_model.column['id'])
        self.queue_tree.append_column(column)
        column = gtk.TreeViewColumn(_("Packages to be merged      "))
        pixbuf = gtk.CellRendererPixbuf()
        column.pack_start(pixbuf, expand = False)
        column.add_attribute(pixbuf, "pixbuf", self.queue_model.column['icon'])
        text = gtk.CellRendererText()
        column.pack_start(text, expand = False)
        column.add_attribute(text, "text", self.queue_model.column['name'])
        self.queue_tree.append_column(column)
        column = gtk.TreeViewColumn(_("Command"))
        text = gtk.CellRendererText()
        column.pack_start(text, expand = True)
        column.add_attribute(text, "text", self.queue_model.column['command'])
        self.queue_tree.append_column(column)
        column = gtk.TreeViewColumn(_("Sender"))
        text = gtk.CellRendererText()
        column.pack_start(text, expand = True)
        column.add_attribute(text, "text", self.queue_model.column['sender'])
        self.queue_tree.append_column(column)
        self.queue_tree.set_model(self.queue_model)
        self.new_window = False
        # set the buttons and menu options sensitive state
        self.set_btn_menus()
        self.show_queue()

    def add(self, package_name, command_string, callback, sender):
        """ Add a process to the queue """
        debug.dprint("TERM_QUEUE: add(): command = " + str(command_string))
        # if the last process was killed, check if it's the same thing
        self.resume_string = None
        skip_first = False
        if self.killed_id:
            debug.dprint("TERM_QUEUE: add(): self.killed is true")
            if package_name == self.get_name() and command_string == self.get_command():
                debug.dprint("TERM_QUEUE: add(): showing resume dialog")
                # The process has been killed, so help the user out a bit
                message = _("The package you selected is already in the emerge queue,\n" \
                            "but it has been killed. Would you like to resume the emerge?")
                result = self.resume_dialog(message)
                if result == gtk.RESPONSE_ACCEPT: # Execute
                    self.cleanup()
                elif result == gtk.RESPONSE_YES: # Resume
                    self.resume_string = " --resume"
                else: # Cancel
                    return False
                # add resume to the command only if it's queue id matches.
                # this allows Resume to restart the queue if the killed process was removed from the queue
                if self.killed_id == self.queue_model.get_value(self.process_iter, self.queue_model.column['id']):
                    command = self.queue_model.get_value(self.process_iter, self.queue_model.column['command'])
                    command += self.resume_string
                    self.queue_model.set_value(self.process_iter, self.queue_model.column['command'], str(command))
            else: # clean up the killed process
                self.cleanup()
        
        if self.resume_string is None:
            debug.dprint("TERM_QUEUE: add(): resume is None")
            # check if the package is already in the emerge queue
            if self.process_iter:
                search_iter = self.process_iter.copy()
                while search_iter:
                    command = self.queue_model.get_value(search_iter, self.queue_model.column['command'])
                    name = self.queue_model.get_value(search_iter, self.queue_model.column['name'])
                    if package_name == name and command_string == command:
                        debug.dprint("TERM_QUEUE: add(): repeat command match")
                        # Let the user know it's already in the list
                        message = _("The package you selected is already in the emerge queue!")
                        debug.dprint("TERM_QUEUE: add(); gettext result = " + _("Error Adding Package To Queue!"))
                        SingleButtonDialog(_("Error Adding Package To Queue!"), None,
                                            message, None, _("OK"))
                        debug.dprint("TERM_QUEUE: add(): returning from match dialog & returning")
                        return  False
                    search_iter = self.queue_model.iter_next(search_iter)
                del search_iter
        # show the window if it isn't visible
        if  self.new_window:
            self.new_window = False
        if self.resume_string is None:
            # add to the queue tab
            insert_iter = self.queue_model.insert_before(None, None)
            self.queue_model.set_data(insert_iter,{'icon':None, 'name':str(package_name), 'command':str(command_string),
                                                                            'id':self.next_id, 'sender':str(sender), 'callback':callback, 'completed': False})
            self.next_id += 1
            if self.queue_paused:
                self.set_icon(PAUSED, self.process_id+1)
        # show the queue tab!
        self.show_queue()
        # if no process is running, let's start one!
        if not self.reader.process_running:
            self.start(skip_first)
        return True

    def cleanup( self ):
        """clean up a killed process in order to continue in the queue without resuming"""
        debug.dprint("TERM_QUEUE: cleanup(); cleaning up killed process")
        self.resume_string = None
        self.resume_available = False
        self.killed_id = None
        self.set_resume(False)
        skip_first = True


    def show_queue(self):
        #if not self.term.tab_showing[TAB_QUEUE]:
        self.term.show_tab(TAB_QUEUE)
        self.queue_menu.set_sensitive(True)

    def restart(self, *widget):
        """re-start the queue"""
        self.queue_paused = False
        self.set_btn_menus()
        self.start(False)

    # skip_first needs to be true for the menu callback
    def start(self, skip_first = True):
        """skips the first item in the queue,
        returns True if all completed, False if pending commands"""
        debug.dprint("TERM_QUEUE: start(%s)" %str(skip_first))
        if self.queue_paused:
            debug.dprint("TERM_QUEUE: start(); queue paused... returning")
            return False
        if skip_first:
            debug.dprint("TERM_QUEUE: start();         ==> skipping killed process")
            self.resume_available = False
            if self.term.tab_showing[TAB_QUEUE]:
                # update the queue tree wait for it to return, it might prevent crashes
                result = self.clicked(self.queue_tree)
            # remove process from list
            self.next()
        # check for pending processes, and run them
        debug.dprint("TERM_QUEUE: start();         ==> check for pending processes, and run them")
        if self.process_iter and not self.get_completed():
                self.run_process()
        else:
            debug.dprint("TERM_QUEUE: start();         ==> try setting to next iter")
            self.next()
            if self.process_iter:
                debug.dprint("TERM_QUEUE: start();         ==> next iter=good; checking process_iter is completed, self.get_completed = %s" %self.get_completed())
                debug.dprint("TERM_QUEUE: start();   new process iter id = %d" %self.get_id())
                if not self.get_completed():
                    self.run_process()
            else:
                debug.dprint("TERM_QUEUE: start(): all processes finished!")
                # re-activate the open/save menu items
                self.save_menu.set_sensitive(True)
                self.save_as_menu.set_sensitive(True)
                self.open_menu.set_sensitive(True)
                return True
        debug.dprint("TERM_QUEUE: start(); finished... returning")
        return False

    def run_process(self):
        command = self.get_command()
        self.process_id = self.get_id()
        debug.dprint("TERM_QUEUE: There are pending processes, running now..id = " + str(self.process_id) + ". [" + command + "]" )
        self.task_completed = False
        self.set_process(EXECUTE)
        self._run(command, self.process_id)
        self.last_run_iter = self.process_iter.copy()

    def next( self):
        debug.dprint("TERM_QUEUE: next();" )
        if self.last_run_iter == None:
            self.process_iter = self.queue_model.get_iter_first()
            debug.dprint("TERM_QUEUE: next(); setting process_iter to iter_first()" )
            self.last_run_iter = self.process_iter.copy()
            return
        elif not self.process_iter:
            self.process_iter = self.last_run_iter.copy()
            debug.dprint("TERM_QUEUE: next(); setting process_iter to last_run_iter" )
        try:
            debug.dprint("TERM_QUEUE: next(); trying to set process_iter to iter_next() current id=%d" %self.get_id())
            self.process_iter = self.queue_model.iter_next(self.last_run_iter)
            debug.dprint("TERM_QUEUE: next(); new process_iter id=%d" %self.get_id())
        except StopIteration:
            debug.dprint("TERM_QUEUE: next();  StopIteration exception" )
            pass

    def pause(self, *widget):
        """pauses the queue"""
        debug.dprint("TERM_QUEUE: pause(); pausing queue at id = " + str(self.process_id+1))
        self.queue_paused = True
        self.set_btn_menus()
        path = self.queue_model.get_path(self.process_iter)[0]
        iter = self.queue_model.get_iter(path +1)
        id = self.queue_model.get_value(iter, self.queue_model.column['id'])
        self.set_icon(PAUSED, id)
        return

    def timer(self, *widget):
        """a queue timer"""
        pass

    def items_switch(self, direction):
        """ Switch two adjacent queue items;
            direction is either 1 [down] or -1 [up] """
        debug.dprint("TERM_QUEUE: Switching queue items.")
        # get the selected iter
        selected_iter = get_treeview_selection(self.queue_tree)
        # get its path
        path = self.queue_model.get_path(selected_iter)[0]
        # only move up if it's not the first entry,
        # only move down if it's not the last entry
        if (not direction and path > 0) or \
            (direction and path < len(self.queue_model)):
            # get the selected value
            selected = self.queue_model.copy(path, 'dict')
            # get the adjacent value
            prev_iter = self.queue_model.get_iter(path + direction)
            prev = self.queue_model.copy(path + direction, 'dict')
            # store selected temporarily so it's not overwritten
            temp = selected.copy()
            #col = self.queue_model.get_column_list()
            prev_id = prev["id"]
            prev_icon = prev["icon"]
            sel_id = selected["id"]
            sel_icon = selected["icon"]
            temp["id"] = prev_id
            prev["id"] = sel_id
            temp["icon"] = prev_icon
            prev["icon"] = sel_icon
            # switch sides and make sure the original is still selected
            self.queue_model.set_data(selected_iter, prev)
            self.queue_model.set_data(prev_iter, temp)
            self.queue_tree.get_selection().select_path(path + direction)
        else:
            debug.dprint("TERM_QUEUE: cannot move first or last item")

        # We're done
        result = self.clicked(self.queue_tree)

    def move_item_up(self, widget):
        """ Move selected queue item up in the queue """
        self.items_switch(-1)

    def move_item_down(self, widget):
        """ Move selected queue item down in the queue """
        self.items_switch(1)

    def remove_item(self, widget):
        """ Remove the selected item from the queue """
        # get the selected iter
        selected_iter = get_treeview_selection(self.queue_tree)
        # find if this item is still in our process list
        name = get_treeview_selection(self.queue_tree, self.queue_model.column['name'])
        if selected_iter:
            self.queue_model.remove(selected_iter)
        self.set_menu_state()
        # We're done

    def clicked(self, *widget):
        """Handle clicks to the queue treeview"""
        debug.dprint("TERM_QUEUE: clicked()")
        # get the selected iter
        selected_iter = get_treeview_selection(self.queue_tree)
        # get its path
        try:
            path = self.queue_model.get_path(selected_iter)[0]
        except:
            debug.dprint("TERM_QUEUE: Couldn't get queue view treeiter path, " \
                    "there is probably nothing selected.")
            return False
        # if the item is already run
        # don't make the controls sensitive and return
        name = get_treeview_selection(self.queue_tree, self.queue_model.column['name'])
        killed = get_treeview_selection(self.queue_tree, self.queue_model.column['killed'])
        id = get_treeview_selection(self.queue_tree, self.queue_model.column['id'])
        #in_list = 0
        if id <= self.process_id: #not in_list or in_list == 1:
            self.move_up.set_sensitive(False)
            self.move_down.set_sensitive(False)
            if id == self.process_id and not killed :
                self.queue_remove.set_sensitive(False)
            else:
                self.queue_remove.set_sensitive(True)
            debug.dprint("TERM_QUEUE: clicked(); finished... returning")
            return True
        # if we reach here it's still in the process list
        # activate the delete item
        self.queue_remove.set_sensitive(True)
        # set the correct directions sensitive
        # shouldn't be able to move the top item up, etc...
        if id == self.process_id + 1 or path == 0:
            self.move_up.set_sensitive(False)
            if path == len(self.queue_model) - 1:
                self.move_down.set_sensitive(False)
            else:
                self.move_down.set_sensitive(True)
        elif path == len(self.queue_model) - 1:
            self.move_up.set_sensitive(True)
            self.move_down.set_sensitive(False)
        else:
            # enable moving the item
            self.move_up.set_sensitive(True)
            self.move_down.set_sensitive(True)
        #debug.dprint("TERM_QUEUE: clicked(); finished... returning")
        return True

    def clear( self ):
        self.queue_model.clear()

    def locate_id( self, process_id ):
        debug.dprint("TERM_QUEUE: locate_id(); looking for process_id = " + str(process_id))
        self.locate_iter = self.queue_model.get_iter_first()
        while self.queue_model.get_value(self.locate_iter,self.queue_model.column['id']) != process_id:
            self.locate_iter = self.queue_model.iter_next(self.locate_iter)
        debug.dprint("TERM_QUEUE: locate_id(); ended up with locate_iter id = %d, looking for %d" \
                %(self.queue_model.get_value(self.locate_iter,self.queue_model.column['id']),process_id))
        return

    def set_icon( self, action_type, process_id, *path):
        debug.dprint("TERM_QUEUE: set_icon(); type = " + str(action_type))
        icon = None
        if action_type == KILLED:
            icon = gtk.STOCK_CANCEL
        elif action_type == FAILED:
            icon = gtk.STOCK_STOP
        elif action_type == COMPLETED:
            icon = gtk.STOCK_APPLY
        elif action_type == EXECUTE:
            icon = gtk.STOCK_EXECUTE
        elif action_type == PAUSED:
            icon = gtk.STOCK_MEDIA_PAUSE
        if icon:
            if path:
                iter = self.queue_model.get_iter(path)
                if not self.get_completed():
                    self.queue_model.set_value(iter, self.queue_model.column['icon'], self.render_icon(icon))
            else:
                try:
                    current_id = self.get_id()
                    #debug.dprint("TERM_QUEUE: set_icon(): process_id = %d, queue_model id = %d" %(process_id, current_id))
                    if process_id == current_id:
                        #debug.dprint("TERM_QUEUE: set_icon(): process_id's match")
                        self.queue_model.set_value(self.process_iter, self.queue_model.column['icon'], self.render_icon(icon))
                    else:
                        #debug.dprint("TERM_QUEUE: set_icon(): process_id's DON'T match")
                        self.locate_id(process_id)
                        #debug.dprint("TERM_QUEUE: set_icon(): back from locate_id()")
                        self.queue_model.set_value(self.locate_iter, self.queue_model.column['icon'], self.render_icon(icon))
                except Exception, e:
                    debug.dprint("TERM_QUEUE: set_icon(): blasted #!* exception %s" %e)

    def render_icon(self, icon):
        """ Render an icon for the queue tree """
        return self.queue_tree.render_icon(icon,
                    size = gtk.ICON_SIZE_MENU, detail = None)

    def set_process( self, action_type):
        if action_type == KILLED:
            #self.set_icon(action_type, self.process_id)
            self.killed_id = self.process_id
        elif action_type in [COMPLETED, FAILED]:
            self.set_completed(True)
        #else:
        self.set_icon(action_type, self.process_id)
        return self.process_id

    def done( self, result):
        debug.dprint("TERM_QUEUE: done(); result = " + str(result))
        self.set_process(result)
        if self.last_run_iter:
            self.last_run_iter = self.process_iter.copy() #self.queue_model.iter_next(self.last_run_iter)
        else:
            self.last_run_iter = self.queue_model.get_iter_first()
        # get the next process
        self.next()
        # check for pending processes, and run them
        self.start(False)
        if self.term.tab_showing[TAB_QUEUE]:
            # update the queue tree
            wait_for = self.clicked()

    def get_callback( self ):
        if self.process_iter:
            return self.queue_model.get_value(self.process_iter, self.queue_model.column['callback'])
        else:
            return None

    def get_command( self ):
        if self.process_iter:
            return self.queue_model.get_value(self.process_iter, self.queue_model.column['command'])
        else:
            return ""

    def get_name( self ):
        if self.process_iter:
            return self.queue_model.get_value(self.process_iter, self.queue_model.column['name'])
        else:
            return ""

    def get_id ( self ):
        if self.process_iter:
            return self.queue_model.get_value(self.process_iter, self.queue_model.column['id'])
        else:
            return 0

    def get_sender( self ):
        if self.process_iter:
            return self.queue_model.get_value(self.process_iter, self.queue_model.column['sender'])
        else:
            return ""

    def get_completed( self ):
        if self.process_iter:
            return self.queue_model.get_value(self.process_iter, self.queue_model.column['completed'])
        else:
            return True

    def get_process( self ):
        name = self.get_name()
        command - get_command()
        callback = self.get_callback()
        id = self.get_id()
        return [name, command, id, callback]

    def set_completed( self, state ):
        """set the queue model completed state (boolean)
            returns a success boolean (optional)"""
        if self.process_iter:
            self.queue_model.set_value(self.process_iter, self.queue_model.column['completed'], state)
            return True
        else:
            return False



    def set_menu_state( self ):
        if self.process_id <  self.next_id - 1:
            self.skip_queue_menu.set_sensitive(True)
        else:
            self.skip_queue_menu.set_sensitive(False)

    def resume( self, *widget):
        # add resume to the command only if it's queue id matches.
        # this allows Resume to restart the queue if the killed process was removed from the queue
        if self.killed_id == self.queue_model.get_value(self.process_iter, self.queue_model.column['id']):
            command = self.get_command()
            command += " --resume"
            self.queue_model.set_value(self.process_iter, self.queue_model.column['command'], command)
        self.start(False)

    def resume_skip_first(self, widget):
        """ Resume killed process, skipping first package """
        command = self.get_command()
        command += " --resume --skipfirst"
        self.queue_model.set_value(self.process_iter, self.queue_model.column['command'], command)
        self.start(False)

    def set_btn_menus( self ):
        """sets the menu and buttons according to the paused state"""
        active = self.queue_paused
        self.play_menu.set_sensitive(active)
        self.play_btn.set_sensitive(active)
        self.pause_menu.set_sensitive(not active)
        self.pause_btn.set_sensitive(not active)

    def resume_dialog(self, message):
        """ Handle response when user tries to re-add killed process to queue """
        window = self.wtree.get_widget("process_window")
        _dialog = gtk.MessageDialog(window, gtk.DIALOG_MODAL,
                                    gtk.MESSAGE_QUESTION,
                                    gtk.BUTTONS_CANCEL, message);
        _dialog.add_button(gtk.STOCK_EXECUTE, gtk.RESPONSE_ACCEPT)
        _dialog.add_button("Resume", gtk.RESPONSE_YES)
        result = _dialog.run()
        _dialog.destroy()
        return result

