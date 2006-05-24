#!/usr/bin/env python

"""
    ============
    | Terminal Queue |
    -----------------------------------------------------------
    A graphical process queue
    -----------------------------------------------------------
    Copyright (C) 2003 - 2005 Fredrik Arnerup, Brian Dolbec, 
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
#import signal, os, pty, threading, time, sre, portagelib
#import datetime, pango, errno
#from dispatcher import Dispatcher
#from process_reader import ProcessOutputReader

from utils import dprint, get_treeview_selection

from constants import *


class ProcessItem:
    def __init__(self, name, command, process_id, callback = None):
        """Structure of a process list item"""
        ## old process item structure [package_name, command_string, iter, callback, self.process_id]
        self.name = name
        self.command = command
        self.callback = callback
        self.killed = False
        # id number for storing in the queue
        self.process_id = process_id
        self.killed_id = None
        self.completed = False

class TerminalQueue:
    """A QUEUE queue"""
    def __init__(self, run_function = None, reader = None, wtree = None, term = None):
        self._run = run_function
        self.reader = reader
        self.wtree = wtree
        self.term = term
        self.queue_paused = False
        self.process_list = []
        self.process_id = 0
        self.next_id = 1
        self.process_iter = None
        self.task_completed = False
        self.killed_id = None
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
        # catch clicks to the queue tree
        self.queue_tree.connect("cursor-changed", self.clicked)
        # setup the queue treeview
        column = gtk.TreeViewColumn(_("Packages to be merged      "))
        pixbuf = gtk.CellRendererPixbuf()
        column.pack_start(pixbuf, expand = False)
        column.add_attribute(pixbuf, "pixbuf", 0)
        text = gtk.CellRendererText()
        column.pack_start(text, expand = False)
        column.add_attribute(text, "text", 1)
        self.queue_tree.append_column(column)
        column = gtk.TreeViewColumn("Command")
        text = gtk.CellRendererText()
        column.pack_start(text, expand = True)
        column.add_attribute(text, "text", 2)
        self.queue_tree.append_column(column)
        self.queue_model = gtk.ListStore(gtk.gdk.Pixbuf,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_INT)
        self.queue_tree.set_model(self.queue_model)
        self.new_window = False
        # set the buttons and menu options sensitive state
        self.set_btn_menus()

    def add(self, package_name, command_string, callback):
        """ Add a process to the queue """
        # if the last process was killed, check if it's the same thing
        self.resume_string = None
        if self.killed_id:
            dprint("TERM_QUEUE: add(): self.killed is true")
            if len(self.process_list) and (package_name == self.process_list[0].name and
                    command_string == self.process_list[0].command):
                dprint("TERM_QUEUE: add(): showing resume dialog")
                # The process has been killed, so help the user out a bit
                message = _("The package you selected is already in the emerge queue,\n" \
                            "but it has been killed. Would you like to resume the emerge?")
                result = self.resume_dialog(message)
                if result == gtk.RESPONSE_ACCEPT: # Execute
                    self.resume_string = ""
                elif result == gtk.RESPONSE_YES: # Resume
                    self.resume_string = " --resume"
                else: # Cancel
                    return False
                # add resume to the command only if it's queue id matches.
                # this allows Resume to restart the queue if the killed process was removed from the queue
                if self.killed_id == self.process_list[0].process_id:
                    self.process_list[0].command += self.resume_string
            else: # clean up the killed process
                dprint("TERM_QUEUE: add(); removing killed process from the list")
                if len(self.process_list):
                    self.process_list = self.process_list[1:]
                self.resume_available = False
                self.killed_id = None
                self.set_resume(False)
        
        if self.resume_string is None:
            dprint("TERM_QUEUE: add(): resume is None")
            # check if the package is already in the emerge queue
            for data in self.process_list:
                if package_name == data.name and command_string == data.command:
                    dprint("TERM_QUEUE: add(): repeat command match")
                    # Let the user know it's already in the list
                    #if data == self.process_list[0]:
                    message = _("The package you selected is already in the emerge queue!")
                    SingleButtonDialog(_("Error Adding Package To Queue!"), None,
                                        message, None, _("OK"))
                    dprint("TERM_QUEUE: add(): returning from match dialog & returning")
                    return  False
        # show the window if it isn't visible
        if  self.new_window:
            # clear process list
            if self.resume_string is not None:
                self.process_list = self.process_list[:1]
            else:
                self.process_list = []
            self.new_window = False
        if self.resume_string is None:
            # add to the queue tab
            insert_iter = self.queue_model.insert_before(None, None)
            self.queue_model.set_value(insert_iter, 0, None)
            self.queue_model.set_value(insert_iter, 1, str(package_name))
            self.queue_model.set_value(insert_iter, 2, str(command_string))
            self.queue_model.set_value(insert_iter, 3, self.next_id)
            # add to the process list only if not resuming
            self.process_list.append( ProcessItem(package_name, command_string,
                                                    self.next_id, callback))
            self.next_id += 1
            if self.queue_paused:
                self.set_icon(PAUSED, self.process_id+1)

        if len(self.process_list) >= 2:
            # if there are 2 or more processes in the list,
            # show the queue tab!
            if not self.term.tab_showing[TAB_QUEUE]:
                self.term.show_tab(TAB_QUEUE)
                self.queue_menu.set_sensitive(True)
        # if no process is running, let's start one!
        if not self.reader.process_running:
            self.start(False)
        return True

    def restart(self, *widget):
        """re-start the queue"""
        self.queue_paused = False
        self.set_btn_menus()
        self.start(False)

    # skip_first needs to be true for the menu callback
    def start(self, skip_first = True):
        """skips the first item in the process_list,
        returns True if all completed, False if pending commands"""
        dprint("TERM_QUEUE: start()")
        if self.queue_paused:
            dprint("TERM_QUEUE: start(); queue paused... returning")
            return False
        if skip_first:
            dprint("TERM_QUEUE: start();         ==> skipping killed process")
            self.resume_available = False
            if self.term.tab_showing[TAB_QUEUE]:
                # update the queue tree wait for it to return, it might prevent crashes
                result = self.clicked(self.queue_tree)
            # remove process from list
            self.next()
        # check for pending processes, and run them
        dprint("TERM_QUEUE: start(): process_list = " + str(self.process_list))
        if len(self.process_list):
            dprint("TERM_QUEUE: There are pending processes, running now... [" + \
                    self.process_list[0].name + "]")
            if not self.process_iter:
                self.process_iter = self.queue_model.get_iter_first()
            self.task_completed = False
            self.set_process(EXECUTE)
            self.process_id = self.process_list[0].process_id
            self._run(self.process_list[0].command, self.process_list[0].process_id)
        else:
            dprint("TERM_QUEUE: start(): all processes finished!")
            # re-activate the open/save menu items
            self.save_menu.set_sensitive(True)
            self.save_as_menu.set_sensitive(True)
            self.open_menu.set_sensitive(True)
            return True
        dprint("TERM_QUEUE: start(); finished... returning")
        return False

    def next( self):
            if len(self.process_list):
                self.process_list = self.process_list[1:]
                try:
                    self.process_iter.iter_next()
                except StopIteration:
                    pass

    def pause(self, *widget):
        """pauses the queue"""
        dprint("TERM_QUEUE: pause(); pausing queue, id = " + str(self.process_id+1))
        self.queue_paused = True
        self.set_btn_menus()
        if len(self.process_list) > 1:
            self.set_icon(PAUSED, self.process_id+1)
        return

    def timer(self, *widget):
        """a queue timer"""
        pass

    def items_switch(self, direction):
        """ Switch two adjacent queue items;
            direction is either 1 [down] or -1 [up] """
        dprint("TERM_QUEUE: Switching queue items.")
        # get the selected iter
        selected_iter = get_treeview_selection(self.queue_tree)
        # get its path
        path = self.queue_model.get_path(selected_iter)[0]
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
                    sel = self.process_list[pos]
                    prev = self.process_list[pos + direction]
                    self.process_list[pos] = prev
                    self.process_list[pos + direction] = sel
                    break
        else:
            dprint("TERM_QUEUE: cannot move first or last item")

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
        name = get_treeview_selection(self.queue_tree, 1)
        for pos in range(len(self.process_list)):
            if name == self.process_list[pos].name:
                # remove the item from the list
                self.process_list = self.process_list[:pos] + \
                                    self.process_list[pos + 1:]
                break
        if selected_iter:
            self.queue_model.remove(selected_iter)
        self.set_menu_state()
        # We're done

    def clicked(self, *widget):
        """Handle clicks to the queue treeview"""
        dprint("TERM_QUEUE: clicked()")
        # get the selected iter
        selected_iter = get_treeview_selection(self.queue_tree)
        # get its path
        try:
            path = self.queue_model.get_path(selected_iter)[0]
        except:
            dprint("TERM_QUEUE: Couldn't get queue view treeiter path, " \
                    "there is probably nothing selected.")
            return False
        # if the item is not in the process list
        # don't make the controls sensitive and return
        name = get_treeview_selection(self.queue_tree, 1)
        in_list = 0
        for pos in range(len(self.process_list)):
            if self.process_list[pos].name == name:
                # set the position in the list (+1 so it's not 0)
                in_list = pos + 1
        if not in_list or in_list == 1:
            self.move_up.set_sensitive(False)
            self.move_down.set_sensitive(False)
            if in_list == 1 and not self.process_list[pos].killed :
                self.queue_remove.set_sensitive(False)
            else:
                self.queue_remove.set_sensitive(True)
            dprint("TERM_QUEUE: clicked(); finished... returning")
            return True
        # if we reach here it's still in the process list
        # activate the delete item
        self.queue_remove.set_sensitive(True)
        # set the correct directions sensitive
        # shouldn't be able to move the top item up, etc...
        if in_list == 2 or path == 0:
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
        #dprint("TERM_QUEUE: clicked(); finished... returning")
        return True

    def clear( self ):
        self.process_list = []
        self.queue_model.clear()

    def locate_id( self, process_id ):
        dprint("TERM_QUEUE: locate_id(); looking for process_id = " + str(process_id))
        self.locate_iter = self.queue_model.get_iter_first()
        while self.queue_model.get_value(self.locate_iter,3) != process_id:
            self.locate_iter = self.queue_model.iter_next(self.locate_iter)
        dprint("TERM_QUEUE: locate_id(); ended up with locate_iter id = %d, looking for %d" \
                %(self.queue_model.get_value(self.locate_iter,3),process_id))
        return

    def set_icon( self, action_type, process_id):
        dprint("TERM_QUEUE: set_icon(); type = " + str(action_type))
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
            try:
                current_id = self.queue_model.get_value(self.process_iter, 3)
                #dprint("TERM_QUEUE: set_icon(): process_id = %d, queue_model id = %d" %(process_id, current_id))
                if process_id == current_id:
                    #dprint("TERM_QUEUE: set_icon(): process_id's match")
                    self.queue_model.set_value(self.process_iter, 0, self.render_icon(icon))
                else:
                    #dprint("TERM_QUEUE: set_icon(): process_id's DON'T match")
                    self.locate_id(process_id)
                    #dprint("TERM_QUEUE: set_icon(): back from locate_id()")
                    self.queue_model.set_value(self.locate_iter, 0, self.render_icon(icon))
            except Exception, e:
                dprint("TERM_QUEUE: set_icon(): blasted #!* exception %s" %e)

    def render_icon(self, icon):
        """ Render an icon for the queue tree """
        return self.queue_tree.render_icon(icon,
                    size = gtk.ICON_SIZE_MENU, detail = None)

    def set_process( self, action_type):
        if action_type == KILLED:
            self.set_icon(action_type, self.process_list[0].process_id)
            self.killed_id = self.process_list[0].process_id
            return self.process_list[0].process_id
        else:
            self.set_icon(action_type, self.process_list[0].process_id)
            return self.process_list[0].process_id

    def done( self, result):
        dprint("TERM_QUEUE: done(); result = " + str(result))
        self.set_process(result)
        # remove process from list
        self.process_list = self.process_list[1:]
        # check for pending processes, and run them
        self.start(False)
        if self.term.tab_showing[TAB_QUEUE]:
            # update the queue tree
            wait_for = self.clicked()

    def get_callback( self ):
        return self.process_list[0].callback

    def get_command( self ):
        return self.process_list[0].command

    def get_name( self ):
        return self.process_list[0].name

    def get_process( self ):
        proc = self.process_list[0]
        return [proc.name, proc.command, proc.process_id, proc.callback] 

    def set_menu_state( self ):
        if len(self.process_list)> 1:
            self.skip_queue_menu.set_sensitive(True)
        else:
            self.skip_queue_menu.set_sensitive(False)

    def resume( self ):
        # add resume to the command only if it's queue id matches.
        # this allows Resume to restart the queue if the killed process was removed from the queue
        if self.killed_id == self.process_list.process_id:
            self.process_list[0].command += " --resume"
        self.start(False)

    def resume_skip_first(self, widget):
        """ Resume killed process, skipping first package """
        self.process_list[0].command += " --resume --skipfirst"
        self.start(False)

    def set_btn_menus( self ):
        """sets the menu and buttons according to the paused state"""
        active = self.queue_paused
        self.play_menu.set_sensitive(active)
        self.play_btn.set_sensitive(active)
        self.pause_menu.set_sensitive(not active)
        self.pause_btn.set_sensitive(not active)
