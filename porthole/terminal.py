#!/usr/bin/env python

"""
    ============
    | Terminal |
    -----------------------------------------------------------
    A graphical process output viewer/filterer and emerge queue
    -----------------------------------------------------------
    Copyright (C) 2003 - 2004 Fredrik Arnerup, Brian Dolbec, and
    Daniel G. Taylor

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
        manager = ProcessManager(environment, preferences)
        manager.add_process(package_name, command_to_run)
        ...
"""

# import external [system] modules
import pygtk; pygtk.require('2.0')
import gtk, gtk.glade, gobject
import signal, os, pty, threading, time
import utils

if __name__ == "__main__":
    # setup our path so we can load our custom modules
    from sys import path
    path.append("/usr/lib/porthole")

# import custom modules
from utils import dprint, get_user_home_dir, SingleButtonDialog, \
                  get_treeview_selection
from version import version

# some constants for the tabs
TAB_PROCESS = 0
TAB_WARNING = 1
TAB_CAUTION = 2
TAB_INFO = 3
TAB_QEUE = 4

class ProcessManager:
    """ Manages qeued and running processes """
    def __init__(self, env = {}, prefs = None):
        """ Initialize """
        # copy the environment and preferences
        self.env = env
        self.prefs = prefs
        self.killed = 0
        self.pid = None
        # process list to store pending processes
        self.process_list = []
        # the window is not visible until a process is added
        self.window_visible = False
        # create the process reader
        self.reader = ProcessOutputReader(self.update, self.process_done)
        # start the reader
        self.reader.start()

    def show_window(self):
        """ Show the process window """
        # load the glade file
        self.wtree = gtk.glade.XML("porthole.glade", "process_window")
        # setup the callbacks
        callbacks = {"on_process_window_destroy" : self.on_process_window_destroy,
                     "on_kill" : self.kill_process,
                     "on_resume_normal" : self.resume_normal,
                     "on_resume_skip_first" : self.resume_skip_first,
                     "on_save_log" : self.save_log,
                     "on_copy" : self.copy_selected,
                     "on_clear" : self.clear_buffer,
                     "on_move_up" : self.move_qeue_item_up,
                     "on_move_down" : self.move_qeue_item_down,
                     "on_remove" : self.remove_qeue_item,
                     "on_quit" : gtk.mainquit}
        self.wtree.signal_autoconnect(callbacks)
        # setup some aliases for easier access
        self.window = self.wtree.get_widget("process_window")
        self.notebook = self.wtree.get_widget("notebook1")
        self.process_text = self.wtree.get_widget("process_text").get_buffer()
        self.warning_text = self.wtree.get_widget("warnings_text").get_buffer()
        self.caution_text = self.wtree.get_widget("cautions_text").get_buffer()
        self.info_text = self.wtree.get_widget("info_text").get_buffer()
        self.queue_tree = self.wtree.get_widget("queue_treeview")
        self.queue_menu = self.wtree.get_widget("queue1")
        self.statusbar = self.wtree.get_widget("statusbar")
        self.resume_menu = self.wtree.get_widget("resume")
        # process output buffer
        self.process_buffer = ''
        # disable the qeue tab until we need it
        self.queue_menu.set_sensitive(gtk.FALSE)
        # setup the qeue treeview
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
        self.warning_tab = self.notebook.get_nth_page(1)
        self.caution_tab = self.notebook.get_nth_page(2)
        self.info_tab = self.notebook.get_nth_page(3)
        self.qeue_tab = self.notebook.get_nth_page(4)
        self.notebook.remove_page(4)
        self.notebook.remove_page(3)
        self.notebook.remove_page(2)
        self.notebook.remove_page(1)
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
            label, tab, pos = "Warnings", self.warning_tab, 1
        elif tab == TAB_CAUTION:
            icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)
            label, tab = "Cautions", self.caution_tab
            # quick hack to make it always show before info & qeue tabs
            pos = self.notebook.page_num(self.info_tab)
            if pos == -1:
                pos = self.notebook.page_num(self.qeue_tab)
                if pos == -1:
                    pos = 2
        elif tab == TAB_INFO:
            icon.set_from_stock(gtk.STOCK_DIALOG_INFO, gtk.ICON_SIZE_MENU)
            label, tab = "Information", self.info_tab
            pos = self.notebook.page_num(self.qeue_tab)
            # set to show before qeue tab
            if pos == -1: pos = 3
        elif tab == TAB_QEUE:
            icon.set_from_stock(gtk.STOCK_EXECUTE, gtk.ICON_SIZE_MENU)
            label, tab, pos = "Emerge Qeue", self.qeue_tab, 4
        # pack the icon and label onto the hbox
        hbox.pack_start(icon)
        hbox.pack_start(gtk.Label(label))
        hbox.show_all()
        # insert the tab
        self.notebook.insert_page(tab, hbox, pos)
        
    def add_process(self, package_name, command_string):
        """ Add a process to the qeue """
        # show the window if it isn't yet
        if not self.window_visible:
            self.show_window()
        # add to the qeue
        iter = self.queue_model.insert_before(None, None)
        self.queue_model.set_value(iter, 0, None)
        self.queue_model.set_value(iter, 1, str(package_name))
        self.queue_model.set_value(iter, 2, str(command_string))
        # add to our process list
        self.process_list.append((package_name, command_string, iter))

        if len(self.process_list) == 2:
            # if this is the 2nd process in the list
            # show the qeue tab!
            self.show_tab(TAB_QEUE)
            self.queue_menu.set_sensitive(gtk.TRUE)
        # if no process is running, let's start this one!
        if not self.reader.process_running:
            self._run(command_string, iter)

    def _run(self, command_string, iter = None):
        """ Run a given command string """
        # we can't be killed anymore
        self.killed = 0
        # set the resume buttons to not be sensitive
        self.resume_menu.set_sensitive(gtk.FALSE)
        if iter:
            self.queue_model.set_value(iter, 0, 
                             self.render_icon(gtk.STOCK_EXECUTE))
        # set process_running so the reader thread reads it's output
        self.reader.process_running = True
        # show a message that the process is starting
        self.append(self.process_text, "*** " + command_string + " ***\n")
        # pty.fork() creates a new process group
        self.pid, self.reader.fd = pty.fork()
        if self.pid == pty.CHILD:  # child
            try:
                # run the command
                shell = "/bin/sh"
                os.execve(shell, [shell, '-c', command_string],
                          self.env)
            except Exception, e:
                # print out the exception
                dprint("Error in child" + e)
                print "Error in child:"
                print e
                os._exit(1)

    def on_process_window_destroy(self, widget, data = None):
        """Window was closed"""
        # kill any running processes
        self.kill()
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

    def append(self, buffer, text):
        """ Append text to a text buffer """
        iter = buffer.get_end_iter()
        buffer.insert(iter, text)

    def update(self, char):
        """ Add text to the buffer """
        # stores line of text in buffer
        # prints line when '\n' is reached
        if char:
            # catch portage escape sequence NOCOLOR bugs
            if ord(char) == 27 or False:
                pass
            elif char == '\b': # backspace
                self.process_buffer = self.process_buffer[:-1]
            elif 32 <= ord(char) <= 127 or char == '\n': # no unprintable
                self.process_buffer += char
                if char == '\n': # newline
                    self.process_text.insert(self.process_text.get_end_iter(), self.process_buffer)
                    self.process_buffer = ''
            elif ord(char) == 13: # carriage return?
                pass

    def process_done(self):
        """ Remove the finished process from the qeue, and
        start the next one if there are any more to be run"""
        # if the last process was killed, stop until the user does something
        if self.killed:
            return
        # display message that process finished
        self.append(self.process_text, "*** process terminated ***\n")
        # set queue icon to done
        iter = self.process_list[0][2]
        self.queue_model.set_value(iter, 0, self.render_icon(gtk.STOCK_APPLY))
        # remove process from list
        self.process_list = self.process_list[1:]
        # check for pending processes, and run them
        if len(self.process_list):
            dprint("TERMINAL: There are pending processes, running now... [" + \
                    self.process_list[0][0] + "]")
            self._run(self.process_list[0][1], self.process_list[0][2])

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
        name, command, iter = self.process_list[0]
        self._run(command + " --resume", iter)

    def resume_skip_first(self, widget):
        """ Resume killed process, skipping first package """
        # pass the normal command along with --resume --skipfirst
        name, command, iter = self.process_list[0]
        self._run(command + " --resume --skipfirst", iter)

    def save_log(self, widget):
        """ Save text buffer to a log """
        # get filename from user
        #filename = ?
        #self.log(filename)
        pass

    def log(self, filename = None):
        """ Log emerge output to a file """
        # get all the process output
        output = self.process_text.get_text(self.textbuffer.get_start_iter(),
                                 self.textbuffer.get_end_iter(), gtk.FALSE)
        if not filename:
            # no filename was specified, so we are making one up
            dprint("LOG: Filename not specified, saving to ~/.porthole/logs")
            filename = get_user_home_dir()
            if os.access(filename + "/.porthole", os.F_OK):
                if not os.access(filename + "/.porthole/logs", os.F_OK):
                    dprint("LOG: Creating logs directory in " + filename +
                           "/.porthole/logs")
                    os.mkdir(filename + "/.porthole/logs")
                filename += "/.porthole/logs/" + "test"
        # open the file, and write our log
        file = open(filename, 'w')
        file.write(output)
        file.close()
        dprint("LOG: Log file written to " + filename)
            

    def copy_selected(self, widget):
        """ Copy selected text to clipboard """
        pass

    def clear_buffer(self, widget):
        """ Clear the text buffer """
        pass

    def move_qeue_item_up(self, widget):
        """ Move selected qeue item up in the qeue """
        pass

    def move_qeue_item_down(self, widget):
        """ Move selected qeue item down in the qeue """
        pass

    def remove_qeue_item(self, widget):
        """ Remove the selected item from the qeue """
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

class ProcessOutputReader(threading.Thread):
    """ Reads output from processes """
    def __init__(self, update_callback, finished_callback):
        """ Initialize """
        threading.Thread.__init__(self)
        # set callbacks
        self.update_callback = update_callback
        self.finished_callback = finished_callback
        self.setDaemon(1)  # quit even if this thread is still running
        self.process_running = False
        self.fd = None

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
                    # send the char to the update callback
                    self.update_callback(char)
                else:
                    # clean up, process is terminated
                    self.process_running = False
                    self.finished_callback()
            else:
                # sleep for .5 seconds before we check again
                time.sleep(.5)


if __name__ == "__main__":
    
    DATA_PATH = "/usr/share/porthole/"

    from sys import argv, exit, stderr
    from getopt import getopt, GetoptError

    try:
        opts, args = getopt(argv[1:], 'lvd', ["local", "version", "debug"])
    except GetoptError, e:
        print >>stderr, e.msg
        exit(1)

    for opt, arg in opts:
        if opt in ("-l", "--local"):
            # running a local version (i.e. not installed in /usr/*)
            DATA_PATH = ""
        elif opt in ("-v", "--version"):
            # print version info
            print "Porthole-Terminal " + version
            exit(0)
        elif opt in ("-d", "--debug"):
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
    prefs = utils.load_user_prefs()
    env = utils.Environment()
    # to test the above classes when run standalone
    test = ProcessManager(env, prefs)
    test.add_process("kde (-vp)", "emerge -vp kde")
    # un-comment the next line to get the qeue to show up
    test.add_process("gnome (-vp)", "emerge -vp gnome")
    test.add_process("gtk+ (-vp)", "emerge -vp gtk+")
    test.add_process("porthole (-vp)", "emerge -vp porthole")
    # start the program loop
    gtk.mainloop()
    # save the prefs to disk for next time
    prefs.save()
