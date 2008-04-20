#!/usr/bin/env python

'''
    Porthole  ProcessOutputReader Class
    It watches a processes output and records it for another process to use

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor,
    Brian Dolbec, Tommy Iorns

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

import signal, os, threading, time, gtk
import errno, string

from porthole.utils import debug
#from porthole.utils.dispatcher import Dispatcher

class ProcessOutputReader(threading.Thread):
    """ Reads output from processes """
    def __init__(self, dispatcher, dprint_output = ''):
        """ Initialize """
        threading.Thread.__init__(self)
        # set callback
        self.dispatcher = dispatcher
        self.setDaemon(1)  # quit even if this thread is still running
        self.process_running = False
        # initialize only, self.fd set by ProcessManager._run()
        self.fd = None
        # initialize only, both set by Processmanager.fill_buffer()
        self.file_input = False
        self.f = None
        # string to store input from process
        self.string = ""
        # lock to prevent losing characters from simultaneous accesses
        self.string_locked = False
        self.record_output = True
        self.dprint_output = dprint_output
        self.dprint_string = ''
        self.die = False

    def run(self):
        """ Watch for process output """
        debug.dprint("PROCESS_READER: ProcessOutputReader(); process id = %d" %os.getpid())
        char = None
        while not self.die:
            if self.process_running or self.file_input:
                # get the output and pass it to self.callback()
                if self.process_running and (self.fd != None):
                    try:
                        char = os.read(self.fd, 1)
                    except OSError, e:
                        if e.args[0] == 5: # 5 = i/o error
                            debug.dprint("PROCESS_READER: ProcessOutputReader: process finished, closing")
                            try:
                                debug.dprint("PROCESS_READER: is self.fd a tty? '%s'" % os.isatty(self.fd))
                                os.close(self.fd)
                                debug.dprint("PROCESS_READER: ProcessOutputReader: closed okay")
                            except Exception, e:
                                # probably already closed
                                debug.dprint("PROCESS_READER: ProcessOutputReader: couldn't close self.fd. exception: %s" % e)
                        else:
                            # maybe the process died?
                            debug.dprint("PROCESS_READER: ProcessOutputReader: .fd OSError: %s" % e)
                        char = None
                elif self.file_input:
                    try:
                        # keep read(number) small so as to not cripple the 
                        # system reading large files.  even 2 can hinder gui response
                        char = self.f.read(1)
                    except OSError, e:
                        debug.dprint("PROCESS_READER: ProcessOutputReader: .f OSError: %s" % e)
                        # maybe the process died?
                        char = None
                if char:
                    # if the string is currently being accessed
                    while(self.string_locked):
                        # wait 50 ms and check again
                        time.sleep(0.05)
                    if self.record_output:
                        # lock the string
                        self.string_locked = True
                        # add the character to the string
                        self.string += char
                        # unlock the string
                        self.string_locked = False
                    if self.dprint_output:
                       self.dprint_string += char
                       if char == '\n':
                           debug.dprint(self.dprint_output + self.dprint_string[:-1])
                           self.dprint_string = ''
                else:
                    # clean up, process is terminated
                    self.process_running = False
                    while self.string != "":
                        #debug.dprint("PROCESS_READER: ProcessOutputReader: waiting for update to finish")
                        # wait for update_callback to finish
                        time.sleep(.5)
                    if self.file_input:
                        self.file_input = False
                    else:
                        gtk.gdk.threads_enter()
                        self.dispatcher()
                        gtk.gdk.threads_leave()
            else:
                # sleep for .5 seconds before we check again
                if time:
                    time.sleep(.5)
        # quit thread

