#!/usr/bin/env python

"""
    ============
    | Terminal Queue |
    -----------------------------------------------------------
    A graphical process queue
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
                self.set(iter, self.column['icon'], data[self.column['icon']],
                                    self.column['name'], data[self.column['name']],
                                    self.column['command'], data[self.column['command']],
                                    self.column['id'], data[self.column['id']],
                                    self.column['sender'], data[self.column['sender']],
                                    self.column['callback'], data[self.column['callback']],
                                    self.column['completed'], data[self.column['completed']]
                            )
            return True
        else:
            return False

class TerminalQueue:
    """A QUEUE queue"""
    def __init__(self, run_function = None, reader = None, wtree = None, term = None, set_resume = None):
        self._run = run_function
        self.reader = reader
        self.wtree = wtree
        self.term = term
        self.set_resume = set_resume
        self.window = wtree.get_widget("process_window")
        self.queue_tree = wtree.get_widget("queue_treeview")
        self.queue_menu = wtree.get_widget("queue1")
        self.resume_menu = self.wtree.get_widget("resume")
        self.skip_first_menu = self.wtree.get_widget("skip_first1")
        self.skip_queue_menu = self.wtree.get_widget("skip_queue")
        self.qmenu_items = { "move_top" : self.wtree.get_widget("move_top"),
                                            "move_up": self.wtree.get_widget("move_up1"),
                                            "move_down" : self.wtree.get_widget("move_down1"),
                                            "move_bottom": self.wtree.get_widget("move_bottom"),
                                            "queue_remove": self.wtree.get_widget("remove1"),
                                            "clear_queue" : self.wtree.get_widget("clear_queue")
                                            }
        # manually assin the keys array since .keys() may not return them in the correct order
        self.qmenu_keys = ["move_top","move_up", "move_down", "move_bottom", "queue_remove", "clear_queue"]
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
        # initialize the model
        self.queue_model = QueueModel()
        # initialize some variables
        self.task_completed = True
        self.queue_paused = False
        self.clear()
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
                skip_first = True

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
            insert_iter = self.queue_model.append() #insert_before(None, None)
            self.queue_model.set_data(insert_iter,{'icon':None, 'name':str(package_name), 'command':str(command_string),
                                                                            'id':self.next_id, 'sender':str(sender), 'callback':callback, 'completed': False})
            if self.queue_paused and self.paused_iter == None:
                self.paused_id = self.process_id+1
                if self.process_iter:
                    self.paused_iter = self.queue_model.iter_next(self.process_iter)
                elif self.next_id == 1:
                    self.paused_iter = self.queue_model.get_iter_first()
                self.set_icon(PAUSED, self.paused_id)
            self.next_id += 1
        # show the queue tab!
        self.show_queue()
        self.qmenu_items["clear_queue"].set_sensitive(True)
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

    def show_queue(self):
        #if not self.term.tab_showing[TAB_QUEUE]:
        self.term.show_tab(TAB_QUEUE)
        self.queue_menu.set_sensitive(True)

    def restart(self, *widget):
        """re-start the queue"""
        debug.dprint("TERM_QUEUE: restart()")
        self.queue_paused = False
        self.set_btn_menus()
        self.set_icon(PENDING, self.paused_id, self.paused_path)
        if self.task_completed:
            debug.dprint("TERM_QUEUE: restart(); task is completed, calling start()")
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
        debug.dprint("TERM_QUEUE: start();         ==> check for pending processes, and run them process_iter = " +str(self.process_iter))
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
        elif self.last_run_iter and not self.process_iter:
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
        if self.queue_paused:
            debug.dprint("TERM_QUEUE: pause(); queue already paused")
            return True
        self.paused_id = self.process_id + 1
        debug.dprint("TERM_QUEUE: pause(); pausing queue at id = " + str(self.paused_id))
        self.queue_paused = True
        self.set_btn_menus()
        self.paused_path = self.queue_model.get_path(self.process_iter)[0] +1
        if self.paused_path < len(self.queue_model):
            self.paused_iter = self.queue_model.get_iter(self.paused_path)
            if self.paused_iter:
                self.set_icon(PAUSED, self.paused_id)
        debug.dprint("TERM_QUEUE: pause(); queue paused... returning, paused_iter = " + str(self.paused_iter))
        return True

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
            # get the adjacent values
            destination_iter = self.queue_model.get_iter(path + direction)
            destination_id = self.queue_model.get_value(destination_iter, self.queue_model.column['id']) 
            destination_icon = self.queue_model.get_value(destination_iter, self.queue_model.column['icon'])
            sel_id = self.queue_model.get_value(selected_iter, self.queue_model.column['id']) 
            sel_icon = self.queue_model.get_value(selected_iter, self.queue_model.column['icon'])
            # switch places and make sure the original is still selected
            self.queue_model.swap(selected_iter, destination_iter)
            self.queue_model.set_value(selected_iter, self.queue_model.column['id'], destination_id)
            self.queue_model.set_value(destination_iter, self.queue_model.column['id'], sel_id)
            if self.paused_path == path or self.paused_path == path + direction:
                self.queue_model.set_value(selected_iter, self.queue_model.column['icon'], destination_icon)
                self.queue_model.set_value(destination_iter, self.queue_model.column['icon'], sel_icon)
                self.paused_iter = self.queue_model.get_iter(self.paused_path)
            self.queue_tree.get_selection().select_path(path + direction)
        else:
            debug.dprint("TERM_QUEUE: cannot move first or last item")

        # We're done, reset queue moves
        result = self.clicked(self.queue_tree)
        del path, selected_iter, destination_iter, sel_id, sel_icon, destination_id, destination_icon

    def move_item_up(self, widget):
        """ Move selected queue item up in the queue """
        self.items_switch(-1)

    def move_item_down(self, widget):
        """ Move selected queue item down in the queue """
        self.items_switch(1)

    def move_item_top(self, widget):
        debug.dprint("TERM_QUEUE: move_item_top()")
        # pause the queue so it does not get messed up while we are moving things
        paused = self.pause()
        my_paused_id = self.queue_model.get_value(self.paused_iter, self.queue_model.column['id'])
        debug.dprint("TERM_QUEUE: move_item_top(); back from paused, paused_iter, id = " + str(self.paused_iter) + ", " + str(my_paused_id))
        # get the selected iter
        selected_iter = get_treeview_selection(self.queue_tree)
        if not selected_iter:
            debug.dprint("TERM_QUEUE: move_item_top(); selected_iter == None, returning, no selection active")
            return False
        #path = self.queue_model.get_path(selected_iter)[0]
        try:
            self.queue_model.move_before(selected_iter, self.paused_iter)
        except:
            debug.dprint("TERM_QUEUE: move_item_top(); exception moving selected_iter before paused_iter")
        debug.dprint("TERM_QUEUE: move_item_top(); paused_id, paused_path = " + str(self.paused_id) + ", " + str(self.paused_path))
        self.set_icon(PENDING, self.paused_id, self.paused_path+1)
        self.paused_iter = selected_iter.copy()
        debug.dprint("TERM_QUEUE: move_item_top(); renumber id's")
        self.renum_ids(self.paused_path, self.paused_id)
        self.set_icon(PAUSED,self.paused_id, self.paused_path)
        # We're done, reset queue moves
        result = self.clicked(self.queue_tree)
        del paused, selected_iter

    def move_item_bottom(self, widget):
        debug.dprint("TERM_QUEUE: move_item_bottom()")
        # pause the queue so it does not get messed up while we are moving things
        paused = self.pause()
        my_paused_id = self.queue_model.get_value(self.paused_iter, self.queue_model.column['id'])
        debug.dprint("TERM_QUEUE: move_item_bottom(); back from paused, paused_iter, id = " + str(self.paused_iter) + ", " + str(my_paused_id))
        # get the selected iter
        selected_iter = get_treeview_selection(self.queue_tree)
        if not selected_iter:
            debug.dprint("TERM_QUEUE: move_item_top(); selected_iter == None, returning, no selection active")
            return False
        path = self.queue_model.get_path(selected_iter)[0]
        try:
            id = self.queue_model.get_value(selected_iter,  self.queue_model.column['id'])
            end_iter = self.queue_model.get_iter(self.next_id-2)
            self.queue_model.move_after(selected_iter, end_iter)
        except Exception, e:
            debug.dprint("TERM_QUEUE: move_item_bottom(); exception moving selected_iter, exception :" + str(e))
        if path == self.paused_path:
            debug.dprint("TERM_QUEUE: move_item_bottom(); detected paused item moved, resetting paused_iter, etc., path, paused_path = "  + str(path) + ", " + str(self.paused_path))
            self.set_icon(PAUSED, self.paused_id, self.paused_path)
            try:
                self.queue_model.set_value(selected_iter, self.queue_model.column['icon'], None)
                self.paused_iter = self.queue_model.get_iter(self.paused_path)
            except Exception, e:
                debug.dprint("TERM_QUEUE: move_item_bottom(); exception resetting paused_iter, exception :" + str(e))
        self.renum_ids(path, id)
        # We're done, reset queue moves
        result = self.clicked(self.queue_tree)
        del end_iter, selected_iter, id, path, paused

    def remove_item(self, widget):
        """ Remove the selected item from the queue """
        # get the selected iter
        selected_iter = get_treeview_selection(self.queue_tree)
        path = self.queue_model.get_path(selected_iter)[0]
        # find if this item is still in our process list
        name = get_treeview_selection(self.queue_tree, self.queue_model.column['name'])
        if selected_iter:
            id = get_treeview_selection(self.queue_tree, self.queue_model.column['id'])
            debug.dprint("TERM_QUEUE: remove_item(); id = " + str(id) + " next_id = " + str(self.next_id) + " paused_id = " + str(self.paused_id))
            self.queue_model.remove(selected_iter)
            # iters are no longer valid.  reset them
            if self.process_id:
                self.locate_id(self.process_id)
                self.process_iter = self.locate_iter.copy()
                self.last_run_iter = self.locate_iter.copy()
            if self.queue_paused:
                self.paused_iter = self.queue_model.get_iter(self.paused_path)
            self.next_id -= 1
            if id < self.next_id:
                self.renum_ids(path, id)
                if id == self.paused_id:
                    self.set_icon(PAUSED, id, path)
        self.set_menu_state()
        # We're done
        del name, id, selected_iter, path

    def renum_ids(self, path, id):
        if not id or  path == None:
            return
        try:
            iter = self.queue_model.get_iter(path)
            while iter:
                self.queue_model.set_value(iter, self.queue_model.column['id'], id)
                iter = self.queue_model.iter_next(iter)
                id += 1
        except:
            debug.dprint("TERM_QUEUE: renum_ids; exception raised during renumber, path, id = " +str(path) + ", " + str(id))
        del iter

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
            del selected_iter
            return False
        # if the item is already run
        # don't make the controls sensitive and return
        name = get_treeview_selection(self.queue_tree, self.queue_model.column['name'])
        killed = get_treeview_selection(self.queue_tree, self.queue_model.column['killed'])
        id = get_treeview_selection(self.queue_tree, self.queue_model.column['id'])
        #in_list = 0
        if id <= self.process_id: #not in_list or in_list == 1:
            state = [False, False, False, False]
            if id == self.process_id and not killed :
                state.append(False)
            else:
                state.append(True)
            self.set_queue_moves(state)
            debug.dprint("TERM_QUEUE: clicked(); finished... returning")
            del selected_iter, id, name, killed, state
            return True
        # if we reach here it's still needs to be processed
        # set the correct directions sensitive
        # shouldn't be able to move the top item up, etc...
        debug.dprint("TERM_QUEUE: clicked(); id = " + str(id) + " next_id = " +str(self.next_id) + " process_id = " + str(self.process_id))
        if id == self.process_id + 1 or path == 0:
            # set move_top and move_up
            state = [False, False]
            debug.dprint("TERM_QUEUE: clicked(); 550 set top,up to False,False")
            if id == self.next_id - 1:
                # set move_down and move_bottom
                state += [False, False]
                debug.dprint("TERM_QUEUE: clicked(); 554 set down,bottom to False,False")
            else:
                state += [True, True]
                debug.dprint("TERM_QUEUE: clicked();  557 set down,bottom to True,True")
        elif id == self.next_id - 1:
            state = [True, True, False, False]
            debug.dprint("TERM_QUEUE: clicked();560 set top,up,down,bottom to True,True,False,False")
        else:
            # enable moving the item
            state = [True, True, True, True]
            debug.dprint("TERM_QUEUE: clicked(); 564 set full move True,True,True,True")
        # activate the delete item in state
        state.append(True)
        self.set_queue_moves(state)
        #debug.dprint("TERM_QUEUE: clicked(); finished... returning")
        del selected_iter, id, name, killed, state
        return True

    def clear( self, *widget ):
        debug.dprint("TERM_QUEUE: clear();")
        # check that task are completed
        if not self.task_completed:
            self.pause()
            return
        self.queue_model.clear()
        self.set_queue_moves([False, False, False, False, False, False])
        if self.queue_paused:
            self.paused_id = 1
            self.paused_path = 0
        else:
            self.paused_id = None
            self.paused_path = None
        self.process_id = 0
        self.next_id = 1
        self.paused_iter = None
        self.process_iter = None
        self.last_run_iter = None
        self.task_completed = True
        self.killed_id = None

    def set_queue_moves(self, state):
        if state:
            for x in range(len(state)):
                if state[x] != None:
                    self.qmenu_items[self.qmenu_keys[x]].set_sensitive(state[x])
        return

    def locate_id( self, process_id ):
        debug.dprint("TERM_QUEUE: locate_id(); looking for process_id = " + str(process_id))
        # try to be smart about it
        path = int(process_id) -1
        try:
            self.locate_iter = self.queue_model.get_iter(path)
            id = self.queue_model.get_value(self.locate_iter,self.queue_model.column['id'])
            if id != process_id:
                #debug.dprint("TERM_QUEUE: locate_id(); ID mismatch, something is out of sink")
                raise Exception("ID mismatch", id, process_id)
        except Exception, e:
            debug.dprint("TERM_QUEUE: locate_id(); execption raised = " + str(e) + " ^^^ path = " + str(path))
            self.locate_iter = self.queue_model.get_iter_first()
            while self.queue_model.get_value(self.locate_iter,self.queue_model.column['id']) != process_id:
                try:
                    self.locate_iter = self.queue_model.iter_next(self.locate_iter)
                except StopIteration:
                    break
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
        elif action_type == PENDING:
            icon = None
        if icon:
            if path:
                debug.dprint("TERM_QUEUE: set_icon(): have valid icon and path")
                iter = self.queue_model.get_iter(path)
                #if not self.get_completed():
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
                    debug.dprint("TERM_QUEUE: set_icon(): blasted #!* exception %s" %str(e))
        else: # no icon
            self.locate_id(process_id)
            #debug.dprint("TERM_QUEUE: set_icon(): back from locate_id()")
            self.queue_model.set_value(self.locate_iter, self.queue_model.column['icon'], None)


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
        self.task_completed = True
        if not self.queue_paused:
            # get the next process
            self.next()
            # check for pending processes, and run them
            self.start(False)
        if self.term.tab_showing[TAB_QUEUE]:
            # update the queue tree
            wait_for = self.clicked()
            del wait_for

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

