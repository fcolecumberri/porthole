#!/usr/bin/env python

'''
    Process
    A graphical process output viewer

    Copyright (C) 2003 - 2004 Fredrik Arnerup and Daniel G. Taylor

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

import pygtk; pygtk.require('2.0')
import gtk, threading
import signal, os, pty
from utils import dprint, get_user_home_dir

class ProcessWindow(threading.Thread):
    RESPONSE_CLOSE = 0
    RESPONSE_KILL = 1
    
    def __init__(self, command, environment = {}, preferences = None,
                 callback = lambda: None):
        # setup prefs
        self.prefs = preferences
        # setup callback
        self.callback = callback
        threading.Thread.__init__(self)
        self.setDaemon(1)  # quit even if this thread is still running
        self.killed = 0
        self.line = ''
        self.pid = self.fd = None
        self.command = command
        self.environment = environment
        self.window = gtk.Dialog(command, None, gtk.DIALOG_NO_SEPARATOR,
                                 ('_Kill', self.RESPONSE_KILL))
        #                                  '_Close', self.RESPONSE_CLOSE))
        table = gtk.TextTagTable()
        self.textbuffer = gtk.TextBuffer(table)
        tag = gtk.TextTag('tt')
        table.add(tag)
        tag.set_property('family', 'Monospace')
        self.textview = gtk.TextView(self.textbuffer)
        self.textview.set_editable(gtk.FALSE)
        self.textview.set_cursor_visible(gtk.FALSE)
        self.wrap_mode = self.textview.set_wrap_mode(gtk.WRAP_WORD)
        self.scroller = gtk.ScrolledWindow()
        self.scroller.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scroller.set_shadow_type(gtk.SHADOW_IN)
        self.scroller.add(self.textview)
        self.window.vbox.pack_start(self.scroller,
                                    gtk.TRUE, gtk.TRUE)
        self.window.connect("realize", self.on_realize)
        self.window.connect("destroy", self.on_destroy)
        self.window.connect("response", self.on_response)
        # set minimum window size
        self.window.set_size_request(400, 300)
        self.window.show_all()
        if self.prefs:
            self.window.resize((self.prefs.emerge.verbose and
                                self.prefs.process.width_verbose or
                                self.prefs.process.width), 
                               self.prefs.process.height)
            # MUST! do this command last, or nothing else will _init__
            # after it until emerge is finished.
            # Also causes runaway recursion.
            self.window.connect("size_request", self.on_size_request)

    def on_size_request(self, window, gbox):
        """Store new size in prefs"""
        width, height = window.get_size()
        if self.prefs.emerge.verbose:
            self.prefs.process.width_verbose = width
        else:
            self.prefs.process.width = width
        self.prefs.process.height = height

    def on_realize(self, window):
        """Start the process and run the thread!"""
        dprint('Process window realizing')
        # pty.fork() creates a new process group
        self.pid, self.fd = pty.fork() 
        if not self.pid:  # child
            try:
                # print os.getpgid(0), os.getpid()
                shell = '/bin/sh'
                os.execve(shell, [shell, '-c', self.command],
                          self.environment)
            except Exception, e:
                print "Error in child:"
                print e
                os._exit(1)

        # only the parent should reach this
        self.start()

    def on_destroy(self, widget, data = None):
        """Window was closed"""
        self.kill()
        self.callback()
        if __name__ == "__main__":
            gtk.main_quit()

    def kill(self):
        """Kill process."""
        # If started and still running
        if self.pid and not self.killed:
            try:
                os.close(self.fd)  # make sure the thread notices
                # negative pid kills process group
                os.kill(-self.pid, signal.SIGKILL)
            except OSError:
                pass
            self.killed = 1

    def on_response(self, widget, response_id):
        """Parse response given from user"""
        self.kill()
        if not __name__ == "__main__":
            self.window.hide()
        self.callback()

    def append(self, text):
        """Append text to the end of the text buffer"""
        iter = self.textbuffer.get_end_iter()
        self.textbuffer.insert_with_tags_by_name(
            iter,
            text.decode('ascii', 'replace'),
            'tt')
        # only scroll when a newline is encountered
        if '\n' in text:
            self.textview.scroll_mark_onscreen(self.textbuffer.get_insert())

    def backspace(self):
        """Delete last character in buffer."""
        end = self.textbuffer.get_end_iter()
        start = end.copy(); start.backward_char()
        self.textbuffer.delete(start, end)

    def del_last_line(self,line_num):
        """Delete the line of text in the buffer"""
        start = self.textbuffer.get_iter_at_line(line_num)
        end = self.textbuffer.get_end_iter()
        self.textbuffer.delete(start,end)

    def log(self, filename = None):
        """Log emerge output to a file"""
        output = self.textbuffer.get_text(self.textbuffer.get_start_iter(),
                                 self.textbuffer.get_end_iter(), gtk.FALSE)
        if not filename:
            dprint("LOG: Filename not specified, saving to ~/.porthole/logs")
            filename = get_user_home_dir()
            if os.access(filename + "/.porthole", os.F_OK):
                if not os.access(filename + "/.porthole/logs", os.F_OK):
                    dprint("LOG: Creating logs directory in " + filename +
                           "/.porthole/logs")
                    os.mkdir(filename + "/.porthole/logs")
                filename += "/.porthole/logs/" + "test"
        file = open(filename, "w")
        file.write(output)
        file.close()
        dprint("LOG: Log file written to " + filename)

    def run(self):
        """The thread."""
        def append(text):
            gtk.threads_enter()
            self.append(text)
            gtk.threads_leave()

        try:
            dprint('begining run of os.read() loop')
            line_num = 0
            dline = ""  # for debug mode
            start_of_line = False
            sol = self.textbuffer.get_start_iter()
            while True:
                text = os.read(self.fd, 1)
                if not text:
                    dprint('unexpected break -- no text')
                    break
##                 elif text == '\033':  # escape
                elif text == "\b":
                    self.backspace()
                elif 32 <= ord(text) <= 127 or text == '\n': # no unprintable
                    if start_of_line and text != '\n':
                        # capture resets to print from start of line without a \n
                        self.del_last_line(line_num)
                        start_of_line = False
                    append(text)
                    if text == '\n':
                        line_num += 1
                        dline += '|eol|'
                        dprint(dline)
                        dline = ""
                    else:
                        dline += text
                elif ord(text) == 13:
                    start_of_line = True
                    dline = dline + '|' + str(ord(text)) + "|"
                    dprint("unprintable char :"+ str(ord(text)))
                else:
                    dline = dline + '|' + str(ord(text)) + "|"
        except OSError:
            pass  # if the process is killed
        except Exception, e:
            append(str(e))
        dprint('end of process capture')
        append('\n')
        append('*** process terminated ***\n')
        self.log()

# Test program,
# run as ./process <any command with parameters>
if __name__ == "__main__":
    from sys import argv
    gtk.threads_init()  # make sure gtk lets other threads run too
    w = ProcessWindow(' '.join(argv[1:]), {"FEATURES": "notitles",
                                           "NOCOLOR": "true"})
    gtk.main()
