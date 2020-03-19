#!/usr/bin/env python

'''
    Porthole Reader Class: CommonReader

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Brian Dolbec, 
    Daniel G. Taylor and Wm. F. Wheeler, Tommy Iorns

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

#import dummy_threading as _threading
import threading, thread
from sys import stderr

class CommonReader(threading.Thread):
    """ Common data reading class that works in a seperate thread """
    def __init__( self ):
        """ Initialize """
        threading.Thread.__init__(self)
        # for keeping status
        self.count = 0
        # we aren't done yet
        self.done = False
        # cancelled will be set when the thread should stop
        self.cancelled = False
        # quit even if thread is still running
        self.setDaemon(1)
        print >>stderr,  "threading.enumerate() = ",threading.enumerate()
        print >>stderr, "this thread is :", thread.get_ident(), ' current thread ', threading.currentThread()

    def please_die( self ):
        """ Tell the thread to die """
        self.cancelled = True

