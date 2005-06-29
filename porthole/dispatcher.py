#! /usr/bin/env python
# Fredrik Arnerup <foo@stacken.kth.se>, 2004-12-19
# Brian Dolbec<dol-sen@telus.net>,2005-3-30

import gobject, os, Queue
from select import select

class Dispatcher:
    """Send signals from a thread to another thread through a pipe
    in a thread-safe manner"""
    def __init__(self, callback, args=None):
        self.callback = callback
        self.callback_args = args
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
            if self.callback_args is not None:
                self.callback(self.callback_args, *self.queue.get())
            else:
                self.callback(*self.queue.get())
        return self.continue_io_watch

