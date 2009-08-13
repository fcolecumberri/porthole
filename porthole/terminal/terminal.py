#!/usr/bin/env python

"""
    ============
    | Terminal |
    -----------------------------------------------------------
    A graphical process output viewer/filter and emerge queue
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
        manager.add(package_name, command_to_run, callback)
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
import signal, os, pty, threading, time #, re
import datetime, pango, errno
from base64 import b64encode, b64decode

#import dbus
#import dbus.service
#from dbus.mainloop.glib import DBusGMainLoop
#DBusGMainLoop(set_as_default=True)

#CONN_INTERFACE = 'Porthole.Terminal'

from gettext import gettext as _

#~ if __name__ == "__main__":
    #~ # setup our path so we can load our custom modules
    #~ from sys import path
    #~ path.append("/usr/lib/porthole")

# import custom modules
from porthole import backends
portage_lib = backends.portage_lib
from porthole.dialogs.simple import SingleButtonDialog, YesNoDialog
from porthole.readers.process_reader import ProcessOutputReader
from porthole.utils.dispatcher import Dispatcher
from porthole.utils import debug
from porthole.utils.utils import get_user_home_dir, get_treeview_selection, estimate, pretend_check
from porthole.version import version
from porthole.terminal.term_queue import TerminalQueue
from porthole.terminal.constants import *
from porthole.terminal.notebook import TerminalNotebook
from porthole.terminal.fileselector import FileSel
from porthole import config

class ProcessManager: #dbus.service.Object):
    """ Manages queued and running processes """
    def __init__(self, env = {}, log_mode = False):
        """ Initialize """
        debug.dprint("TERMINAL: ProcessManager; process id = %d ****************" %os.getpid())
        
        #self.sysbus = dbus.SystemBus()
        #self.sesbus = dbus.SessionBus()
        #bus_name = dbus.service.BusName(CONN_INTERFACE)
        #object_path = '/Porthole/Terminal'
        #dbus.service.Object.__init__(self, bus_name, object_path)
        #dbus.service.Object.__init__(self, self.sesbus, path)
        #self.dbus_obj = self.sesbus.get_object(CONN_INTERFACE, object_path)
        #self.dbus_if = dbus.Interface(self.dbus_obj, CONN_INTERFACE)
        #services = dbus_if.ListNames()
        
        if log_mode:
            self.title = "Porthole Log Viewer"
        else:
            self.title = "Porthole-Terminal"
            debug.dprint(self.title)
        self.log_mode = log_mode
        #self.Semaphore = threading.Semaphore()
        # copy the environment
        self.env = env
        self.killed = 0
        self.pid = None
        self.Failed = False
        self.isPretend = False
        self.file_input = False
        self.callback_armed = False
        self.killed_id = None
        # the window is not visible until a process is added
        self.window_visible = False
        self.task_completed = True
        self.confirm = False
        self.status_text = ''
        # filename and serial #
        self.directory = None
        self.filename = None
        self.untitled_serial = -1
        self.allow_delete = False
        self.clipboard = gtk.Clipboard()
        # create the process reader
        self.reader = ProcessOutputReader(Dispatcher(self.process_done))
        # Added a Line Feed check in order to bypass code if LF's are not used ==> CR only
        self.LF_check = True #False
        #self.cr_count = 0
        self.line_num = 0
        self.badpassword_check = False
        self.badpassword_linenum = 0
 

    def reset_buffer_update(self):
        # clear process output buffer
        self.process_buffer = ''
        self.line_buffer = ''
        # set some persistent variables for text capture
        self.catch_seq = False
        self.escape_seq = "" # to catch the escape sequence in
        self.first_cr = True  # first time cr is detected for a line
        self.overwrite_till_nl = False  # overwrite until after a '\n' detected for this line
        self.resume_line = None
        self.lastchar = ''
        self.cr_flag = False
        self.b_flag = False
        self.force_buffer_write = True

    def show_window(self):
        """ Show the process window """
        
        self.reset_buffer_update()
        
        if hasattr(self, 'window'):
            debug.dprint("TERMINAL: show_window(): window attribute already set... attempting show")
            # clear text buffer and emerge queue, hide tabs
            self.clear_buffer(None)
            debug.dprint("TERMINAL: show_window(): buffers cleared... clearing queue model...")
            self.process_queue.clear()
            debug.dprint("TERMINAL: show_window(): queue model cleared")
            for tab in [TAB_WARNING, TAB_CAUTION, TAB_INFO]: #, TAB_QUEUE]:
                self.term.hide_tab(tab)
            # re-set base values for textviews
            attributes = gtk.TextView().get_default_attributes()
            default_fg = attributes.fg_color
            default_bg = attributes.bg_color
            default_weight = attributes.font.get_weight()
            default_font = attributes.font.to_string()
            self.term.last_text = [] # re-set last-text
            widget_labels = ["process_text", "warnings_text", "cautions_text", "info_text"]
            for x in widget_labels:
                self.term.last_text.append('\n')
                view = self.wtree.get_widget(x)
                if x == "process_text" or config.Prefs.terminal.all_tabs_use_custom_colors:
                    fg, bg, weight = config.Prefs.TAG_DICT['default']
                    font = config.Prefs.terminal.font
                    if bg: view.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(bg))
                    else: view.modify_base(gtk.STATE_NORMAL, default_bg)
                    if fg: view.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(fg))
                    else: view.modify_text(gtk.STATE_NORMAL, default_fg)
                    view.modify_font(pango.FontDescription(font or default_font))
                else:
                    view.modify_base(gtk.STATE_NORMAL, default_bg)
                    view.modify_text(gtk.STATE_NORMAL, default_fg)
                    view.modify_font(pango.FontDescription(default_font))
            # re-set misc. stuff
            self.term.command_start = None
            # re-set text tags
            self.term.set_tags()
            # show window
            self.window.show()
            self.window_visible = True
            #gobject.timeout_add(100, self.update)
            debug.dprint("TERMINAL: show_window(): returning")
            return True
        # load the glade file
        self.wtree = gtk.glade.XML(config.Prefs.DATA_PATH + config.Prefs.use_gladefile,
                                   "process_window", config.Prefs.APP)
        # these need to be before the callbacks
        # setup some aliases for easier access
        self.window = self.wtree.get_widget("process_window")
        self.notebook = self.wtree.get_widget("notebook1")
        self.statusbar = self.wtree.get_widget("statusbar")
        self.resume_menu = self.wtree.get_widget("resume")
        self.skip_first_menu = self.wtree.get_widget("skip_first1")
        self.save_menu = self.wtree.get_widget("save1")
        self.save_as_menu = self.wtree.get_widget("save_as")
        self.open_menu = self.wtree.get_widget("open")
        # Initialize event widget source
        self.event_src = None
        # get a mostly blank structure to hold a number of widgets & settings
        self.term = TerminalNotebook(self.notebook, self.wtree, self.set_statusbar)
        # queue init
        self.process_queue = TerminalQueue(self._run, self.reader, self.wtree, self.term, self.set_resume)
        
        # setup the callbacks
        callbacks = {"on_process_window_destroy" : self.on_process_window_destroy,
                     "on_kill" : self.kill_process,
                     "on_resume_normal" : self.process_queue.resume,
                     "on_resume_skip_first" : self.process_queue.resume_skip_first,
                     "on_skip_queue" : self.process_queue.start,
                     "on_save_log" : self.do_save,
                     "on_save_log_as" : self.do_save_as,
                     "on_open_log" : self.do_open,
                     "on_copy" : self.term.copy_selected,
                     "on_clear" : self.clear_buffer,
                     "on_quit" : self.menu_quit,
                     "on_process_text_key_press_event" : self.on_pty_keypress,
                     "on_move_up" : self.process_queue.move_item_up,
                     "on_move_down" : self.process_queue.move_item_down,
                     "on_move_top": self.process_queue.move_item_top,
                     "on_move_bottom": self.process_queue.move_item_bottom,
                     "on_remove" : self.process_queue.remove_item,
                     "on_clear_queue": self.process_queue.clear,
                     "on_resume_queue_activate" : self.process_queue.restart,
                     "on_play_queue_button_clicked" : self.process_queue.restart,
                     "on_timer_button_clicked" : self.process_queue.timer,
                     "on_timer_activate" : self.process_queue.timer,
                     "on_pause_button_clicked" : self.process_queue.pause,
                     "on_pause_activate" : self.process_queue.pause
                     }
        self.wtree.signal_autoconnect(callbacks)

        # initialize to None
        self.pid = None
        # used to skip a killed queue item if killed
        self.resume_available = False
        # translate the title
        self.title = _(self.title)
        # set the window title
        self.window.set_title(self.title)
        self.window.connect("window_state_event", self.new_window_state)
        self.minimized = False
        # flag that the window is now visible
        self.window_visible = True
        self.window.connect('delete-event', self.confirm_delete)

        # set keyboard focus to process tab
        self.wtree.get_widget("process_text").grab_focus()
        # set the custom timer icon
        #self.wtree.get_widget('timer_button_img').set_from_file(config.Prefs.DATA_PATH + "pixmaps/porthole-clock-20x20.png")
        self.timer_btn = self.wtree.get_widget('timer_button')
        self.timer_btn.set_sensitive(False)
        #self.wtree.get_widget('timer_image').set_from_file(config.Prefs.DATA_PATH + "pixmaps/porthole-clock-20x20.png")
        self.timer_menuitem = self.wtree.get_widget('timer')
        self.timer_menuitem.set_sensitive(False)
        # start the reader
        self.reader.start()
        gobject.timeout_add(100, self.update)

        if config.Prefs:
            self.window.resize((config.Prefs.emerge.verbose and
                                config.Prefs.terminal.width_verbose or
                                config.Prefs.terminal.width), 
                                config.Prefs.terminal.height)
            # MUST! do this command last, or nothing else will _init__
            # after it until emerge is finished.
            # Also causes runaway recursion.
            self.window.connect("size_request", self.on_size_request)

    #~ @dbus.service.method(CONN_INTERFACE, in_signature='ss', out_signature='', sender_keyword='sender')
    #~ def request_add( self, name, command, sender ):
        #~ sender_name = self.dbus_if.GetNameOwner(sender)
        #~ self.add(name, command, self.reply , sendername + " (" +sender + ")")

    def add( self, name, command, callback, sender = _('Non-DBus') ):
        # show the window if it isn't visible
        if not self.window_visible:
            self.show_window()
            # clear process list, too
            if self.reader.process_running:
                debug.dprint("*** TERM_QUEUE: add_process: There should be NO process running here!")
                debug.dprint("*** TERM_QUEUE: add_process: Dangerous things may happen after this point!")
            self.process_queue.new_window = True

        self.process_queue.add(name, command, callback, sender)

    def reply():
        pass

    def on_size_request(self, window, gbox):
        """ Store new size in prefs """
        # get the width and height of the window
        width, height = window.get_size()
        # set the preferences
        if config.Prefs.emerge.verbose:
            config.Prefs.terminal.width_verbose = width
        else:
            config.Prefs.terminal.width = width
        config.Prefs.terminal.height = height

    def new_window_state(self, widget, event):
        """set the minimized variable to change the title to the same as the statusbar text"""
        #debug.dprint("TERMINAL: window state event: %s" % event.new_window_state) # debug print statements
        #debug.dprint(event.changed_mask
        state = event.new_window_state
        if state & gtk.gdk.WINDOW_STATE_ICONIFIED:
            #debug.dprint("TERMINAL: new_window_state; event = minimized")
            self.minimized = True
            self.window.set_title(self.status_text)
        elif self.minimized:
            #debug.dprint("TERMINAL: new_window_state; event = unminimized")
            self.minimized = False
            self.window.set_title(self.title)
        return False

    def _run(self, command_string, command_id):
        """ Run a given command string """
        debug.dprint("TERMINAL: running command string '%s'" % command_string)
        # we can't be killed anymore
        self.killed = 0
        self.command_id = command_id
        # reset back to terminal mode in case it is not
        self.log_mode = False
        self.warning_count = 0
        self.caution_count = 0
        self.Failed = False
        self.isPretend = pretend_check(command_string)
        self.term.set_startmark()
        # set the resume buttons to not be sensitive
        self.resume_menu.set_sensitive(False)
        self.save_menu.set_sensitive(False)
        self.save_as_menu.set_sensitive(False)
        self.open_menu.set_sensitive(False)
        # show a message that the process is starting
        self.term.append_all("*** " + command_string + " ***\n", True, 'command')
        self.set_statusbar("*** " + command_string + " ***")
        # pty.fork() creates a new process group
        if self.reader.fd:
            if os.isatty(self.reader.fd):
                debug.dprint("TERMINAL: self.reader already has fd, closing")
                os.close(self.reader.fd)
            else:
                debug.dprint("TERMINAL: self.reader has fd but seems to be already closed.")
                try:
                    os.close(self.reader.fd)
                except OSError, e:
                    debug.dprint("TERMINAL: error closing self.reader.fd: %s" % e)
        self.pid, self.reader.fd = pty.fork()
        if self.pid == pty.CHILD:  # child
            try:
                # run the commandbuffer.tag_table.lookup(tagname)
                shell = "/bin/sh"
                os.execve(shell, [shell, '-c', command_string],
                          self.env)
                
            except Exception, e:
                # print out the exception
                debug.dprint("TERMINAL: Error in child" + e)
                #print "Error in child:"
                #print e
                os._exit(1)
        else:
            # set process_running so the reader thread reads it's output
            self.reader.process_running = True
            debug.dprint("TERMINAL: pty process id: %s ******" % self.pid)

    def menu_quit(self, widget):
        """ hide the window when the close button is pressed """
        debug.dprint("TERMINAL: menu_quit()")
        if self.confirm_delete():
            return
        debug.dprint("TERMINAL: menu==>quit clicked... starting destruction")
        self.window.destroy()

    def on_process_window_destroy(self, widget, data = None):
        """Window was closed"""
        debug.dprint("TERMINAL: on_process_window_destroy()")
        # kill any running processes
        self.kill_process()
        # make sure to reset the process list
        self.process_queue.clear() 
         # the window is no longer showing
        self.window_visible = False
        self.wtree = None
        if __name__ == "__main__":
            # if running standalone, quit
            try:
                gtk.main_quit()
            except:
                gtk.mainquit()
        if self.reader.isAlive():
            self.reader.die = "Please"
            debug.dprint("TERMINAL: reader process still alive - killing...")
            self.reader.join()
            debug.dprint("okay!")
            del self.reader
        debug.dprint("TERMINAL: on_process_window_destroy(); ...destroying now")
        self.window.destroy()
        del self.window

    def kill_process(self, widget = None, confirm = False):
        """ Kill currently running process """
        # Prevent conflicts while changing process queue
        #self.Semaphore.acquire()
        #debug.dprint("TERMINAL: kill_process; Semaphore acquired")

        if not self.reader.process_running and not self.file_input:
            debug.dprint("TERMINAL: No running process to kill!")
            # We're finished, release semaphore
            #self.Semaphore.release()
            #debug.dprint("TERMINAL: kill_process; Semaphore released")
            debug.dprint("TERMINAL: leaving kill_process")
            return True
        self.kill()
        if self.log_mode:
            debug.dprint("LOG: set statusbar -- log killed")
            self.set_statusbar(_("***Log Process Killed!"))
        else:
            #self.Semaphore.release()
            #debug.dprint("TERMINAL: kill_process; Semaphore released")
            self.was_killed()
            return True

        # We're finished, release semaphore
        #self.Semaphore.release()
        #debug.dprint("TERMINAL: kill_process; Semaphore released")
        debug.dprint("TERMINAL: leaving kill_process")
        return True

    def kill(self):
        """Kill process."""
        if self.log_mode:
            self.reader.file_input = False
            debug.dprint("LOG: kill() wait for reader to notice")
            # wait for ProcessOutputReader to notice
            time.sleep(.5)
            debug.dprint("LOG: kill() -- self.reader.f.close()")
            self.reader.f.close()
            self.file_input = False
            debug.dprint("LOG: leaving kill()")
            return True
        # If started and still running
        if self.pid and not self.killed:
            try:
                if self.reader.fd:
                    os.write(self.reader.fd, "\x03")
                    debug.dprint("TERMINAL: ctrl-C sent to process")
                    self.resume_available = True
                    # make sure the thread notices
                    #os.kill(self.pid, signal.SIGKILL)
                    #os.close(self.reader.fd)
                else: # just in case there is anything left
                    # negative pid kills process group
                    os.kill(-self.pid, signal.SIGKILL)
            except OSError, e:
                debug.dprint("TERMINAL: kill(), OSError %s" % e)
                pass
            self.killed = True
            self.task_completed = True
            if self.term.tab_showing[TAB_QUEUE]:
                # update the queue tree
                #self.Semaphore.release()
                self.process_queue.clicked()
                #self.Semaphore.acquire()
        debug.dprint("TERMINAL: leaving kill()")
        return True

    def was_killed(self):
        debug.dprint("TERMINAL: was_killed(); setting queue icon")
        # set the queue icon to killed
        self.killed_id = self.process_queue.set_process(KILLED)
        debug.dprint("TERMINAL: was_killed(); setting resume to sensitive")
        # set the resume buttons to sensitive
        self.set_resume(True)
        debug.dprint("TERMINAL: leaving was_killed()")


    def confirm_delete(self, widget = None, *event):
        if self.allow_delete:
            retval = False
        else:
            debug.dprint("TERMINAL: disallowing delete event")
            retval = True
        if not self.task_completed:
            err = _("Confirm: Kill the Running Process")
            dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                    gtk.MESSAGE_QUESTION,
                                    gtk.BUTTONS_YES_NO, err);
            result = dialog.run()
            dialog.destroy()
            if result != gtk.RESPONSE_YES:
                debug.dprint("TERMINAL: confirm_delete(); stopping delete")
                return True
            debug.dprint("TERMINAL: confirm_delete(); confirmed")
            if self.kill_process():
                self.task_completed = True
        # hide the window. if retval is false it'll be destroyed soon.
        self.window.hide()
        self.window_visible = False
        # now also seems like the only good time to clean up.
        debug.dprint("TERMINAL: cleaning up zombie emerge processes")
        while True:
            try:
                m = os.wait() # wait for any child processes to finish
                debug.dprint("TERMINAL: process %s finished, status %s" % m)
            except OSError, e:
                if e.args[0] == 10: # 10 = no process to kill
                    break
                debug.dprint("TERMINAL: OSError %s" % e)
                break
        debug.dprint("TERMINAL: done cleaning up emerge processes")
        return retval

    def force_buffer_write_timer(self):
        """ Indicates that text in the buffer should be displayed immediately. """
        #debug.dprint("TERMINAL: force_buffer_write_timer(): setting True")
        self.force_buffer_write = True
        return False # don't repeat call

    def newline(self):
        #debug.dprint("TERMINAL: newline(); self.cr_count = %d, self.line_num = %d" %(self.cr_count, self.line_num))
        tag = None
        self.b_flag = False
        if self.line_buffer != self.process_buffer:
            overwrite = True
        else:
            overwrite = False
        # check for a failed password
        #debug.dprint("TERMINAL: newline(); self.line_num = %d, self.badpassword_linenum = %d, check = %s" \
        #                    %(self.line_num, self.badpassword_linenum,str(self.badpassword_check)))
        if self.badpassword_check and self.badpassword_linenum == self.line_num:
            debug.dprint("TERMINAL: newline(); checking for a bad password...")
            #if self.line_buffer.startswith("Sorry, try again."):
            if  config.Config.isBadPassword(self.line_buffer):
                debug.dprint("TERMINAL: newline(); found a bad password...deleting bad password")
                if hasattr(self, 'password'):
                    #delete it so it gets a new one
                    del self.password
            # check is done reset to False
            self.badpassword_check = False
            debug.dprint("TERMINAL: newline(); bad password check complete...resetting bad_password_check = False")
        #if config.Config.isEmerge(self.process_buffer):
        elif config.Config.isEmerge(self.line_buffer):
            # add the pkg info to all other tabs to identify fom what
            # pkg messages came from but no need to show it if it isn't
            tag = 'emerge'
            self.term.append(TAB_INFO, self.line_buffer, tag)
            self.term.append(TAB_WARNING, self.line_buffer, tag)
            if not self.file_input:
                self.set_file_name(self.line_buffer)
                self.set_statusbar(self.line_buffer[:-1])
                self.resume_line = self.line_buffer
                if self.callback_armed:
                    self.do_callback()
                    self.callback_armed = False
                        
        #~ if config.Config.isUnmerge(self.line_buffer):
            #~ tag = 'emerge'
            #~ if not self.file_input:
                #~ self.set_statusbar(self.line_buffer[:-1])
                #~ self.resume_line = self.line_buffer
                #~ if self.callback_armed:
                    #~ self.do_callback()
                    #~ self.callback_armed = False
                        
        elif config.Config.isAction(self.line_buffer):
            if not self.term.tab_showing[TAB_INFO]:
                self.term.show_tab(TAB_INFO)
                self.term.view_buffer[TAB_INFO].set_modified(True)
            tag = 'caution'
            self.term.append(TAB_INFO, self.line_buffer, tag)
                        
        #elif config.Config.isInfo(self.process_buffer):
        elif config.Config.isInfo(self.line_buffer):
            # Info string has been found, show info tab if needed
            if not self.term.tab_showing[TAB_INFO]:
                self.term.show_tab(TAB_INFO)
                self.term.view_buffer[TAB_INFO].set_modified(True)
                            
            # Check for fatal error
            #if config.Config.isError(self.process_buffer):
            if config.Config.isError(self.line_buffer):
                self.Failed = True
                tag = 'error'
                self.term.append(TAB_INFO, self.line_buffer, tag)
            else:
                tag = 'info'
                self.term.append(TAB_INFO, self.line_buffer)
                            
            # Check if the info is ">>> category/package-version merged"
            # then set the callback to return the category/package to update the db
            #debug.dprint("TERMINAL: update(); checking info line: %s" %self.process_buffer)
            if (not self.file_input) and config.Config.isMerged(self.line_buffer):
                self.callback_package = self.line_buffer.split()[1]
                self.callback_armed = True
                debug.dprint("TERMINAL: update(); Detected sucessfull merge of package: " + self.callback_package)
            #else:
                #debug.dprint("TERMINAL: update(); merge not detected")
                        
        elif config.Config.isWarning(self.line_buffer):
            # warning string has been found, show info tab if needed
            if not self.term.tab_showing[TAB_WARNING]:
                self.term.show_tab(TAB_WARNING)
                self.term.view_buffer[TAB_WARNING].set_modified(True)
            # insert the line into the info text buffer
            tag = 'warning'
            self.term.append(TAB_WARNING, self.line_buffer)
            self.warning_count += 1
                        
        elif config.Config.isCaution(self.line_buffer):
            # warning string has been found, show info tab if needed
            if not self.term.tab_showing[TAB_CAUTION]:
                self.term.show_tab(TAB_CAUTION)
                self.term.view_buffer[TAB_CAUTION].set_modified(True)
            # insert the line into the info text buffer
            tag = 'caution'
            self.term.append(TAB_CAUTION, self.line_buffer)
            self.caution_count += 1
                        
        if self.overwrite_till_nl:
            #debug.dprint("TERMINAL: '\\n' detected in overwrite mode, calling overwrite()")
            self.term.overwrite(TAB_PROCESS, self.line_buffer[:-1], tag)
            self.term.append(TAB_PROCESS, '\n', tag)
            self.overwrite_till_nl = False
        elif overwrite and tag:
            #debug.dprint("TERMINAL: overwrite and tag = True, calling overwrite()")
            self.term.overwrite(TAB_PROCESS, self.line_buffer[:-1], tag)
            self.term.append(TAB_PROCESS, '\n', tag)
        else:
            self.term.append(TAB_PROCESS, self.process_buffer, tag)
        self.process_buffer = ''  # reset buffer
        self.line_buffer = ''
        self.line_num += 1

    def update(self):
        """ Add text to the buffer """
        # stores line of text in buffer
        # if the string is locked, we'll get it on the next round
        #cr_flag = False   # Carriage Return flag
        if self.reader.string_locked:
            return True
        if not self.window_visible:
            self.reader.string = ''
            return True
        # lock the string
        self.reader.string_locked = True
        for char in self.reader.string:
            if char:
                ord_char = ord(char)
                #if ord_char <=31 or (ord_char >=127 and ord_char<=160):
                #    debug.dprint("TERMINAL: adding control char to buffer: %s" % (ord_char ))
                # if we find a CR without a LF, switch to overwrite mode
                if self.cr_flag:
                    # gcc and some emerge output no longer outputs a LF so addded a bypass switch
                    # no, seems gcc is sending 2 <cr>'s before a LF
                    if (self.LF_check and ord_char != 10): # or ord(self.lastchar) == 13:
                        #debug.dprint("TERMINAL: self.LF_check = True and the next char != 10, but = %d, self.cr_count = %d, self.lastchar = %d" %(ord_char, self.cr_count,ord(self.lastchar)))
                        tag = None
                        if self.first_cr:
                            #debug.dprint("TERMINAL: self.first_cr = True")
                            self.term.append(TAB_PROCESS, self.process_buffer, tag)
                            self.first_cr = False
                            #debug.dprint("TERMINAL: resetting self.first_cr to True, setting self.overwrite_till_nl = True")
                            self.overwrite_till_nl = True
                            self.process_buffer = ''
                            self.line_buffer = ''
                        # overwrite until after a '\n' detected for this line
                        else:
                            #debug.dprint("TERMINAL: self.first_cr = False, calling overwrite()")
                            self.term.overwrite(TAB_PROCESS, self.process_buffer, tag)
                            self.process_buffer = ''
                            self.line_buffer = ''
                    else:
                        # reset for next time
                        self.first_cr = True
                    self.cr_flag = False
                # catch portage escape sequences for colour and terminal title
                if self.catch_seq and ord_char != 27:
                    self.escape_seq += char
                    if self.escape_seq.startswith('['):
                        # xterm escape sequence. terminated with:
                        # @ (63), A to Z (64 to 90), a to z (97 to 122), {,|,},~ (123 to 126)
                        # and _perhaps_ '`' (96) (an erroneous character may be output to the
                        # screen after this)
                        # also note: this list may not be exhaustive......
                        if 63 <= ord_char <= 90 or 96 <= ord_char <= 126:
                            self.catch_seq = False
                            #debug.dprint('escape_seq = ' + self.escape_seq)
                            self.term.parse_escape_sequence(self.escape_seq)
                            self.escape_seq = ''
                    elif self.escape_seq.startswith(']'):
                        if ord_char == 7 or self.escape_seq.endswith('\x1b\\'):
                            self.catch_seq = False
                            self.term.parse_escape_sequence(self.escape_seq)
                            self.escape_seq = ''
                    elif self.escape_seq.startswith('k'): # note - terminated with chr(27) + \
                        if self.escape_seq.endswith('\x1b\\'): # \x1b = chr(27)
                            self.catch_seq = False
                            self.term.parse_escape_sequence(self.escape_seq)
                            self.escape_seq = ''
                    else: # don't know how to handle this - stop now
                        self.catch_seq = False
                        self.term.parse_escape_sequence(self.escape_seq)
                        self.escape_seq = ''
                elif ord_char == 27:
                    if self.escape_seq.startswith("k"):
                        self.escape_seq += char
                    else:
                        self.catch_seq = True
                        self.term.append(TAB_PROCESS, self.process_buffer, None)
                        self.process_buffer = ''
                elif char == '\b' : # backspace
                    # this is used when portage prints ">>> Updating Portage Cache"
                    # it uses backspaces to update the number. So on each update
                    # we display the old value (better than waiting for \n)
                    # (it's also used for the spinner and some other stuff)
                    if self.lastchar != '\b': # i.e. starting to delete old value
                        if not self.b_flag: # initial display
                            self.term.append(TAB_PROCESS, self.line_buffer)
                        else: # every other display until \n is found
                            #debug.dprint("TERMINAL: self.b_flag = True, calling overwrite()")
                            self.term.overwrite(TAB_PROCESS, self.line_buffer)
                    #self.process_buffer = ''
                    self.line_buffer = self.line_buffer[:-1]
                    self.b_flag = True
                    #debug.dprint("TERMINAL: self.b_flag = True, setting self.overwrite_till_nl = True")
                    self.overwrite_till_nl = True
                elif ord(char) == 13:  # carriage return
                    self.cr_flag = True
                    #self.cr_count += 1
                    #debug.dprint("TERMINAL: update(); <cr> detected, self.cr_count = %d, self.lastchar = %d" %(self.cr_count, ord(self.lastchar)))
                elif 32 <= ord_char <= 127 or ord_char == 10: # no unprintable
                    self.process_buffer += char
                    self.line_buffer += char
                    if ord_char == 10: # newline
                        #debug.dprint("TERMINAL: update(); <LF> detected, self.cr_count = " + str(self.cr_count))
                        self.newline()
                    elif self.force_buffer_write:
                        if self.overwrite_till_nl:
                            self.term.overwrite(TAB_PROCESS, self.line_buffer)
                            self.line_buffer = ''
                        else:
                            self.term.append(TAB_PROCESS, self.process_buffer)
                            self.process_buffer = ''
                        self.force_buffer_write = False
                        gobject.timeout_add(200, self.force_buffer_write_timer)
                self.lastchar = char
        else: # if reader string is empty... maybe waiting for input
            if self.force_buffer_write and self.process_buffer:
                #debug.dprint("TERMINAL: update(): nothing else to do - forcing text to buffer")
                if self.overwrite_till_nl:
                    #self.term.overwrite(TAB_PROCESS, self.line_buffer)
                    #self.line_buffer = ''
                    pass
                else:
                    self.term.append(TAB_PROCESS, self.process_buffer)
                    self.process_buffer = ''
                self.force_buffer_write = False
                gobject.timeout_add(200, self.force_buffer_write_timer)
                # perhaps sudo is waiting for a password
                # note: the prompt is set to "Password:" in the command string
                # to override any default.
                if self.line_buffer.startswith("Password:"):
                    self.do_password_popup()
        self.reader.string = ""
        #debug.dprint("TERMINAL: update() checking file input/reader finished")
        if self.file_input and not self.reader.file_input: # reading file finished
            debug.dprint("LOG: update()... end of file input... cleaning up")
            self.term.view_buffer[TAB_PROCESS].set_modified(False)
            self.finish_update()
            self.set_statusbar(_("*** Log loading complete : %s") % self.filename)
            self.reader.f.close()
            self.file_input = False
        # unlock the string
        self.reader.string_locked = False
        return True
    
    def do_password_popup(self):
        """ Pops up a dialog asking for the users password """
        if hasattr(self, 'password'): # have already entered password, forward it
            debug.dprint("TERMINAL: do_password_popup: forwarding previously-entered password to sudo")
            self.forward_password()
            return
        debug.dprint("TERMINAL: do_password_popup: asking for user's password")
        dialog = gtk.Dialog("Password Required",
                            self.window,
                            gtk.DIALOG_MODAL & gtk.DIALOG_DESTROY_WITH_PARENT,
                            (_("_Cancel"), gtk.RESPONSE_CANCEL));
        dialog.vbox.set_spacing(10)
        #dialog.set_has_separator(False)
        dialog.set_border_width(10)
        command = self.process_queue.get_command()
        #if command.startswith('sudo '):
        if 'sudo -p "Password:'  in command:
            command = command[command.index('sudo -p "Password:')+21:]
            label = gtk.Label(_("'sudo -p Password: ' requires your user password to perform the command:\n'%s'")
                            % command)
        elif command.startswith('sudo '):
            command = command[command.index('sudo ')+5:]
            label = gtk.Label(_("'sudo: ' requires your user password to perform the command:\n'%s'")
                            % command)
            
        elif 'su -c ' in command:
            command = command[command.index('su -c ')+6:]
            label = gtk.Label(_("'su' requires the root password to perform the command:\n'%s'")
                            % command)
        elif command.startswith('su '):
            command = command[command.index('su ')+3:]
            label = gtk.Label(_("'su' requires the root password to perform the command:\n'%s'")
                            % command)
        else:
            label = gtk.Label(_("Password Required to perform the command:\n'%s'")
                            % command)
        dialog.vbox.pack_start(label)
        label.show()
        hbox = gtk.HBox()
        label = gtk.Label(_("Password: "))
        entry = gtk.Entry()
        entry.set_property("visibility", False) # password mode
        entry.connect("activate", self.get_password_cb, dialog)
        hbox.pack_start(label, expand=False)
        hbox.pack_start(entry, expand=True)
        dialog.vbox.pack_start(hbox)
        hbox.show_all()
        gtk.gdk.threads_enter()
        result = dialog.run()
        gtk.gdk.threads_leave()
        debug.dprint("TERMINAL: do_password_popup(): result %s" % result)
        dialog.destroy()
        if result == gtk.RESPONSE_CANCEL:
            self.kill_process()
            #self.write_to_term('\x03') # control-C
            self.term.append(TAB_PROCESS, '^C')
            # reset resume to false since emerge had not been called yet
            self.set_resume(False)

    def get_password_cb(self, entrywidget, entrydialog):
        """ Callback to get new password from the entry dialog"""
        self.password = b64encode(entrywidget.get_text())
        self.forward_password()
        entrydialog.response(1)

    def forward_password(self):
        """ Callback to pass a password to the terminal process """
        if self.reader.fd:
            try:
                os.write(self.reader.fd, b64decode(self.password) + '\n')
            except OSError:
                debug.dprint(" * TERMINAL: forward_password(): Error forwarding password!")
            self.term.append(TAB_PROCESS, '********')
            # set flag to watch for a bad password string
            self.badpassword_check = True
            self.badpassword_linenum = self.line_num + 1
            debug.dprint(" * TERMINAL: forward_password(): setting badpassword_check = True")
        else:
            debug.dprint("TERMINAL: forward_password(): reader has no open file descriptor, skipping")
    
    def on_pty_keypress(self, widget, event):
        """Catch keypresses in the terminal process window, and forward
        them on to the emerge process.
        """
        #debug.dprint("TERMINAL: on_pty_keypress(): string %s" % event.string)
        self.write_to_term(event.string)
        if event.string == "\003":
            debug.dprint("TERMINAL: on_pty_keypress(): cntl-c detected")
            # set the resume sensitive & set the queue icon to killed
            self.was_killed()
            self.killed = True
    
    def write_to_term(self, text=''):
        """Forward text to the terminal process. Very low tech."""
        if self.reader.fd:
            try:
                os.write(self.reader.fd, text)
                return True
            except OSError, e:
                debug.dprint(" * TERMINAL: write_to_term(): Error '%s' writing text '%s'"
                        % (e, text))
                return False
    
    def set_file_name(self, line):
        """extracts the ebuild name and assigns it to self.filename"""
        x = line.split("/")
        y = x[1].split(" ")
        name = y[0]
        self.filename = name + "." + self.term.view_buffer_types[TAB_PROCESS]
        debug.dprint("TERMINAL: New ebuild detected, new filename: " + self.filename)
        return

    def set_statusbar(self, string):
        """Update the statusbar without having to use push and pop."""
        self.statusbar.pop(0)
        self.statusbar.push(0, string)
        self.status_text = string
        if self.minimized:
            self.window.set_title(string)

    def finish_update(self):
        if self.warning_count != 0:
            self.term.append(TAB_INFO, _("*** Total warnings count for merge = %d \n")\
                        %self.warning_count, 'note')
            if not self.term.tab_showing[TAB_INFO]:
                self.term.show_tab(TAB_INFO)
                self.term.view_buffer[TAB_INFO].set_modified(True)
        if self.caution_count != 0:
            self.term.append(TAB_INFO, _("*** Total cautions count for merge = %d \n")\
                        %self.caution_count, 'note')
            if not self.term.tab_showing[TAB_INFO]:
                self.term.show_tab(TAB_INFO)
                self.term.view_buffer[TAB_INFO].set_modified(True)
        return

    def process_done(self, *args):
        """ Remove the finished process from the queue, and
        start the next one if there are any more to be run"""
        debug.dprint("TERMINAL: process_done(): process id: %s" % os.getpid())
        debug.dprint("TERMINAL: process_done(): process group id: %s" % os.getpgrp())
        debug.dprint("TERMINAL: process_done(): parent process id: %s" % os.getppid())
        
        # reset to None, so next one starts properly
        self.reader.fd = None
        # clean up finished emerge process
        try:
            m = os.waitpid(self.pid, 0) # wait for any child processes to finish
            debug.dprint("TERMINAL: process %s finished, status %s" % m)
        except OSError, e:
            if not e.args[0] == 10: # 10 = no process to kill
                debug.dprint("TERMINAL: OSError %s" % e)
        # if the last process was killed, stop until the user does something
        if self.killed:
            # display message that process has been killed
            killed_string = _(KILLED_STRING)
            self.term.append_all(killed_string,True)
            self.set_statusbar(killed_string[:-1])
            self.reader.string = ''
            self.reset_buffer_update()
            # remove stored password
            #if hasattr(self, 'password'):
                #del self.password
            debug.dprint("TERMINAL: process_done; self.killed = True, returning")
            return
            
        # If the user did an emerge --pretend, we print out
        # estimated build times on the output window
        if self.isPretend:
            self.estimate_build_time()
        self.finish_update()
        # display message that process finished
        terminaled_string = _(TERMINATED_STRING)
        self.term.append_all(terminaled_string,True)
        self.set_statusbar(terminaled_string[:-1])
        self.do_callback()
        self.callback_armed = False
        # set queue icon according to success or failure
        if self.Failed:
            self.process_queue.done(FAILED)
        else:
            self.process_queue.done(COMPLETED)
        self.task_completed = True

    def do_callback(self):
        # try to get a callback
        callback = self.process_queue.get_callback()
        # if there is a callback set, call it
        if callback:
            debug.dprint("TERMINAL: do_callback(); Calling callback()")
            callback()
            # callback(self.callback_package)

    def extract_num(self, line):
        """extracts the number of packages from the 'emerge (x of y) cat/package
        for setting the resume menu entries"""
        first = line.index("(") + 1
        last = line.index(")")
        num = line[first:last].split()
        return int(num[2]) - int(num[0])

    def set_resume(self, active):
        """sets the resume menu to the desired state,
        checking and setting the individual entries to their correct state
        at the time """
        if active:
            if self.resume_line:
                remaining = self.extract_num(self.resume_line)
            else:
                remaining = 0
                
            if remaining:  # > 0
                self.skip_first_menu.set_sensitive(True)
            else:
                self.skip_first_menu.set_sensitive(False)
            self.resume_menu.set_sensitive(True)
            self.process_queue.set_menu_state()
        else:
            self.resume_menu.set_sensitive(False)

    def estimate_build_time(self):
        """Estimates build times based on emerge --pretend output"""
        start_iter = self.term.view_buffer[TAB_PROCESS].get_iter_at_mark(self.term.command_start)
        output = self.term.view_buffer[TAB_PROCESS].get_text(start_iter,
                                 self.term.view_buffer[TAB_PROCESS].get_end_iter(), False)
        package_list = []
        total = datetime.timedelta()        
        for line in output.split("\n"):
            if config.Config.ebuild_re.match(line):
                tokens = line.split(']')
                tokens = tokens[1].split()
                tmp_name = portage_lib.get_name(tokens[0])
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
                    self.term.append(TAB_PROCESS, _(
                            "*** Unfortunately, you don't have enough " \
                            "logged information about the listed packages " \
                            "to calculate estimated build times " \
                            "accurately.\n"), 'note')
                    return None
            self.term.append(TAB_PROCESS, _(
                        "*** Based on the build history of these packages " \
                        "on your system, I can estimate that emerging them " \
                        "usually takes, on average, " \
                        "%(days)d days, %(hours)d hrs, %(minutes)d mins, and %(seconds)d secs.\n") %
                        {'days': total.seconds // (24 * 3600),\
                         'hours': (total.seconds % (24 * 3600)) // 3600,\
                         'minutes': ((total.seconds % (24 * 3600))  % 3600) //  60,\
                         'seconds': ((total.seconds % (24 * 3600))  % 3600) %  60}, 'note')
            self.term.append(TAB_PROCESS, _(
                        "*** Note: If you have a lot of programs running on " \
                        "your system while porthole is emerging packages, " \
                        "or if you have changed your hardware since the " \
                        "last time you built some of these packages, this " \
                        "estimate may be inaccurate.\n"), 'note')

    def set_save_buffer(self):
        """Sets the save info for the notebook tab's visible buffer"""
        debug.dprint("TERMINAL: Entering set_save_buffer")
        self.buffer_num = self.term.current_tab
        self.buffer_to_save = self.term.view_buffer[self.buffer_num]
        self.buffer_type = self.term.view_buffer_types[self.buffer_num]
        debug.dprint("TERMINAL: set_save_buffer: " + str(self.buffer_num) + " type: " + self.buffer_type)
        return (self.buffer_num != None)

    def open_ok_func(self, filename):
        """callback function from file selector"""
        debug.dprint("LOG: Entering callback open_ok_func")
        # set terminal to log mode if not already
        self.log_mode = True
        if not self.window_visible: self.show_window()
        if not self.fill_buffer(filename):
            self.set_statusbar(_("*** Unknown File Loading error"))
            return False
        else:
            self.filename = filename
            self.set_statusbar(_("*** File Loading... Processing...")) 
            return True;

    def do_open(self, widget):
        """opens the file selector for file to open"""
        debug.dprint("LOG: Entering do_open")
        if not self.directory:
            self.set_directory()
        try:
            FileSel(self.title + _(": Open log File")).run(self.window,
                                                        self.directory+"*.log",
                                                        self.open_ok_func)
        except:
            FileSel(self.title + _(": Open log File")).run(None,
                                                        self.directory+"*.log",
                                                        self.open_ok_func)
        debug.dprint("LOG: leaving do_open")

    def do_save_as(self, widget):
        """determine buffer to save as and saves it"""
        debug.dprint("LOG: Entering do_save_as")
        if not self.directory:
            self.set_directory()
        if self.set_save_buffer():
            result = self.check_buffer_saved(self.buffer_to_save, False)
        else:
            debug.dprint("TERMINAL: Error: buffer is already saved")

    def do_save(self, widget):
        """determine buffer to save and proceed"""
        debug.dprint("LOG: Entering do_save")
        if not self.directory:
            self.set_directory()
        if not self.filename:
            self.do_save_as(widget)
        else:
            if self.set_save_buffer():
                result = self.check_buffer_saved(self.buffer_to_save, True)
            else:
                debug.dprint("LOG: set_save_buffer error")

    def save_as_buffer(self):
        debug.dprint("LOG: Entering save_as_buffer")
        return FileSel(self.title + ": Save File").run(self.window,
                                                           self.filename,
                                                           self.save_as_ok_func)

    def save_as_ok_func(self, filename):
        """file selector callback function"""
        debug.dprint("LOG: Entering save_as_ok_func")
        old_filename = self.filename

        if (not self.filename or filename != self.filename):
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

        if self.save_buffer():
            return True
        else:
            self.filename = old_filename
            return False

    def set_directory(self):
        """sets the starting directory for file selection"""
        if not self.directory:
            # no directory was specified, so we are making one up
            debug.dprint("LOG: directory not specified, setting to default: %s" %config.Prefs.LOG_FILE_DIR)
            self.directory = config.Prefs.LOG_FILE_DIR
            ##self.directory = get_user_home_dir()
            ##if os.access(self.directory + "/.porthole", os.F_OK):
            ##    if not os.access(self.directory + "/.porthole/logs", os.F_OK):
            ##        debug.dprint("LOG: Creating logs directory in " + self.directory +
            ##               "/.porthole/logs")
            ##        os.mkdir(self.directory + "/.porthole/logs")
            ##    self.directory += "/.porthole/logs/"
                #os.chdir(self.directory)
 
    def pretty_name(self):
        """pre-assigns generic filename & serial #"""
        debug.dprint("LOG: Entering pretty_name")
        # check if filename set and set the extension to the correct buffer type 
        if self.filename and self.filename[:7] != "Untitled":
            filename = os.path.basename(self.filename)
            filename = filename.split(".")
            newname = filename[0]
            for x in filename[1:-1]:
                newname += ("." + x)
            self.filename = newname + "." + self.buffer_type
            debug.dprint(self.filename)
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
        debug.dprint("LOG: Entering fill_buffer")
        self.clear_buffer(None)
        self.warning_count = 0
        self.caution_count = 0
        self.set_statusbar(_("*** Loading File : %s") % self.filename)
        try:
            self.reader.f = open(filename, "r")
        except IOError, (errnum, errmsg):
            d = {"filename" : filename, "errmsg" : errmsg}
            err = _("Cannot open file '%(filename)s': %(errmsg)s") % d
            dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                       gtk.MESSAGE_INFO,
                                       gtk.BUTTONS_OK, err);
            result = dialog.run()
            dialog.destroy()
            return False

        self.file_input = True
        self.reader.file_input = True
        return True

    def save_buffer(self):
        """save the contents of the buffer"""
        debug.dprint("LOG: Entering save_buffer")
        result = False
        have_backup = False
        if not self.filename:
            return False

        bak_filename = self.filename + "~"
        try:
            os.rename(self.filename, bak_filename)
        except (OSError, IOError), (errnum, errmsg):
            if errnum != errno.ENOENT:
                d = {"filename" : self.filename, "bak_filename" : bak_filename, "errmsg" : errmsg}
                err = _("Cannot back up '%(filename)s' to '%(bak_filename)s': %(errmsg)s") % d
                dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                           gtk.MESSAGE_INFO,
                                           gtk.BUTTONS_OK, err);
                dialog.run()
                dialog.destroy()
                return False

        have_backup = True
        self.set_statusbar(_("*** saving file: %s") % self.filename)
        try:
            file = open(self.filename, "w")
            # if buffer is "Process" strip line numbers
            if self.buffer_num == TAB_PROCESS:
                start = self.buffer_to_save.get_start_iter()
                while not start.is_end():
                    end = start.copy(); end.forward_line()
                    chars = self.buffer_to_save.get_text(start, end, False)
                    file.write(chars[7:])
                    chars = ""
                    start.forward_line()
                    
            else: # save the entire buffer
                start, end = self.buffer_to_save.get_bounds()
                chars = self.buffer_to_save.get_text(start, end, False)
                file.write(chars)

            file.close()
            self.buffer_to_save.set_modified(False)
            result = True
        except IOError, (errnum, errmsg):
            err = ("Error writing to '%s': %s") % (self.filename, errmsg)
            dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                       gtk.MESSAGE_INFO,
                                       gtk.BUTTONS_OK, err);
            dialog.run()
            dialog.destroy()

        if not result and have_backup:
            try:
                os.rename(bak_filename, self.filename)
            except OSError, (errnum, errmsg):
                d = {"filename" : self.filename, "bak_filename" : bak_filename, "errmsg" : errmsg}
                err = _("Can't restore backup file '%(filename)s' to '%(bak_filename)s': %(errmsg)s\nBackup left as '%(bak_filename)s'") % d
                dialog = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL,
                                           gtk.MESSAGE_INFO,
                                           gtk.BUTTONS_OK, err);
                dialog.run()
                dialog.destroy()

        self.set_statusbar(_("*** File saved : %s") % self.filename)
        debug.dprint("LOG: Buffer saved, exiting")
        return result

    def check_buffer_saved(self, _buffer, save = False):
        """checks if buffer has been modified before saving again"""
        debug.dprint("LOG: Entering check_buffer_saved")
        self.filename = self.pretty_name()
        if _buffer.get_modified():
            if save:
                msg = _("Save log to '%s'?") % self.filename
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
                    return False
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
                return False
            else:
                return False

    def clear_buffer( self, *widget ):
        self.term.clear_buffers()
        self.filename = None
        


# very out of date!
#~ if __name__ == "__main__":

    #~ def callback():
        #~ """ Print a message to display that callbacks are working"""
        #~ debug.dprint("TERMINAL: Callback caught...")
    
    #~ DATA_PATH = "/usr/share/porthole/"

    #~ from sys import argv, exit, stderr
    #~ from getopt import getopt, GetoptError
    #~ import utils.debug

    #~ try:
        #~ opts, args = getopt(argv[1:], "lvd", ["local", "version", "debug"])
    #~ except GetoptError, e:
        #~ print >>stderr, e.msg
        #~ exit(1)

    #~ for opt, arg in opts:
        #~ if opt in ('-l', "--local"):
            #~ # running a local version (i.e. not installed in /usr/*)
            #~ DATA_PATH = ""
        #~ elif opt in ('-v', "--version"):
            #~ # print version info
            #~ print "Porthole-Terminal " + version
            #~ exit(0)
        #~ elif opt in ('-d', "--debug"):
            #~ debug.debug = True
            #~ debug.dprint("Debug printing is enabled")
    #~ # change dir to your data path
    #~ if DATA_PATH:
        #~ from os import chdir
        #~ chdir(DATA_PATH)
    #~ # make sure gtk lets threads run
    #~ gtk.threads_init()
    #~ # setup our app icon
    #~ myicon = gtk.gdk.pixbuf_new_from_file("pixmaps/porthole-icon.png")
    #~ gtk.window_set_default_icon_list(myicon)
    #~ # load prefs
    #~ prefs_additions = [
        #~ ["DATA_PATH",DATA_PATH],
        #~ ["APP",None],
        #~ ["i18n_DIR",None],
        #~ ["RUN_LOCAL",None]
    #~ ]
    #~ prefs = utils.PortholePreferences(prefs_additions)
    #~ env = utils.environment()
    #~ # to test the above classes when run standalone
    #~ test = ProcessManager(env, prefs)
    #~ test.title = "Porthole-Terminal"
    #~ test.process_queue.add("kde (-vp)", "emerge -vp kde", callback)
    #~ # un-comment the next line to get the queue to show up
    #~ test.process_queue.add("gnome (-vp)", "emerge -vp gnome", callback)
    #~ test.process_queue.add("gtk+ (-vp)", "emerge -vp gtk+", callback)
    #~ test.process_queue.add("bzip2 (-v)", "emerge -v bzip2", callback)
    #~ # start the program loop
    #~ gtk.mainloop()
    #~ # save the prefs to disk for next time
    #~ prefs.save()
