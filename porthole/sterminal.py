#!/usr/bin/env python

'''
    sterminal
    Runs a command without a user interface

    Copyright (C) 2003 - 2008  Brian Dolbec, Fredrik Arnerup and Daniel G. Taylor

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


import datetime
id = datetime.datetime.now().microsecond
print "STERMINAL: id initialized to ", id

import signal, os, pty, threading, time
import errno, string

from porthole.utils import utils, debug
from porthole.utils.dispatcher import Dispatcher
# next, avoid a circular import and go direct
from porthole.readers.process_reader import ProcessOutputReader


class SimpleTerminal:
    """Porthole's simple terminal to run a command without an interface
    """
    def __init__(self, command, need_output,  dprint_output='', callback=None):
        self.command = command
        self.pid = None
        # create the process reader
        self.reader = ProcessOutputReader(Dispatcher(self.cleanup), dprint_output)
        self.reader.record_output = need_output
        self.callback = callback
        # start the reader
        self.reader.start()
    
    def _run(self):
        debug.dprint("STERMINAL: run_app(); process id = %d *******************" %os.getpid())
        env = utils.environment()
        # next section probably not needed since this will usually be run one time only
        if self.reader.fd:
            if os.isatty(self.reader.fd):
                debug.dprint("STERMINAL: self.reader already has fd, closing")
                os.close(self.reader.fd)
            else:
                debug.dprint("STERMINAL: self.reader has fd but seems to be already closed.")
                try:
                    os.close(self.reader.fd)
                except OSError, e:
                    debug.dprint("STERMINAL: error closing self.reader.fd: %s" % e)
        
        self.pid, self.reader.fd = pty.fork()
        if self.pid == pty.CHILD:  # child
            try:
                # run the command
                shell = "/bin/sh"
                os.execve(shell, [shell, '-c', self.command],
                    env)
            except Exception, e:
                debug.dprint("STERMINAL: Error in child" + e)
                os._exit(1)
        else:
            # set process_running so the reader thread reads it's output
            self.reader.process_running = True
            debug.dprint("STERMINAL: pty process id: %s ******" % self.pid)
        return
    
    def cleanup(self):
        # reset to None, so next one starts properly
        self.reader.fd = None
        self.reader.die = True
        # clean up finished process
        try:
            m = os.waitpid(self.pid, 0) # wait for any child processes to finish
            debug.dprint("STERMINAL: process %s finished, status %s" % m)
        except OSError, e:
            if not e.args[0] == 10: # 10 = no process to kill
                debug.dprint("STERMINAL: OSError %s" % e)
        if self.callback:
            self.callback()
