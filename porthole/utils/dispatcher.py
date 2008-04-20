#! /usr/bin/env python
'''
    Porthole dispatcher module
    Holds common debug functions for Porthole

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Brian Dolbec

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

# Fredrik Arnerup <foo@stacken.kth.se>, 2004-12-19
# Brian Dolbec<dol-sen@telus.net>,2005-3-30

import gobject, os, Queue
from select import select

class Dispatcher:
    """Send signals from a thread to another thread through a pipe
    in a thread-safe manner"""
    def __init__(self, callback_func, *args, **kwargs):
        self.callback = callback_func
        self.callback_args = args
        self.callback_kwargs = kwargs
        self.continue_io_watch = True
        self.queue = Queue.Queue(0) # thread safe queue
        self.pipe_r, self.pipe_w = os.pipe()
        gobject.io_add_watch(self.pipe_r, gobject.IO_IN, self.on_data)
        
    def __call__(self, *args):
        """Emit signal from thread"""
        self.queue.put(args)
        # write to pipe afterwards
        os.write(self.pipe_w, "X")
    
    def on_data(self, source, cb_condition):
        if select([self.pipe_r],[],[], 0)[0] and os.read(self.pipe_r,1):
            if self.callback_args:
                args = self.callback_args + self.queue.get()
                self.callback(*args, **self.callback_kwargs)
            else:
                self.callback(*self.queue.get(), **self.callback_kwargs)
        return self.continue_io_watch

