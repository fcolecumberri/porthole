#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk, threading
from popen2 import Popen4
from os import kill
import signal
from sys import argv

class ProcessWindow(threading.Thread):
    RESPONSE_CLOSE = 0
    RESPONSE_KILL = 1
    
    def __init__(self, command):
        threading.Thread.__init__(self)
        self.setDaemon(1)  # quit even if this thread is still running
        self.killed = 0
        self.line = ''
        self.pipe = None
        self.command = command
        self.window = gtk.Dialog(command, None, gtk.DIALOG_NO_SEPARATOR,
                                 ('_Kill', self.RESPONSE_KILL,
                                  '_Close', self.RESPONSE_CLOSE))
        table = gtk.TextTagTable()
        self.textbuffer = gtk.TextBuffer(table)
        tag = gtk.TextTag('tt')
        table.add(tag)
        tag.set_property('family', 'Monospace')
        textview = gtk.TextView(self.textbuffer)
        textview.set_editable(gtk.FALSE)
        textview.set_cursor_visible(gtk.FALSE)
        self.scroller = gtk.ScrolledWindow()
        self.scroller.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scroller.set_shadow_type(gtk.SHADOW_IN)
        self.scroller.add(textview)
        self.window.vbox.pack_start(self.scroller,
                                    gtk.TRUE, gtk.TRUE)

        self.window.connect("realize", self.on_realize)
        self.window.connect("destroy", self.on_destroy)
        self.window.connect("response", self.on_response)
        self.window.set_size_request(400, 600)
        self.window.show_all()

    def on_realize(self, window):
        self.start()  # run thread

    def on_destroy(self, widget, data = None):
        self.kill()
        gtk.main_quit()

    def kill(self):
        """Kill process."""
        # If started and still running
        if self.pipe and self.pipe.poll() == -1 and not self.killed:
            self.pipe.fromchild.close()  # make sure the thread notices
            #print "Killing ", self.pipe.pid
            kill(self.pipe.pid, signal.SIGKILL)
            self.killed = 1

    def on_response(self, widget, response_id):
        if response_id == self.RESPONSE_CLOSE:
            self.kill()
            gtk.main_quit()
        elif response_id == self.RESPONSE_KILL:
            self.kill()

    def append_line(self, line):
        """Append a line to the end of the text buffer"""
        iter = self.textbuffer.get_end_iter()
        self.textbuffer.insert_with_tags_by_name(
            iter,
            (line + '\n').decode('ascii', 'replace'),
            'tt')
        adj = self.scroller.get_vadjustment()
        adj.set_value(adj.upper - adj.page_size)

    def run(self):
        """The thread."""
        def append_line(line):
            gtk.threads_enter()
            self.append_line(line)
            gtk.threads_leave()
        self.pipe = Popen4(self.command)
        try:
            for line in self.pipe.fromchild:
                append_line(line[:-1])
        except ValueError:
            pass  # if the process is killed
        self.pipe.wait()  # or poll() will return -1 in the main thread
        append_line('')
        append_line('*** process terminated ***')

# Test program,
# run as ./porthole <any command with parameters>
if __name__ == "__main__":
    gtk.threads_init()  # make sure gtk lets other threads run too
    w = ProcessWindow(' '.join(argv[1:]))
    gtk.main()
