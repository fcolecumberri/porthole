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

import pygtk; pygtk.require("2.0")
import gtk
from time import sleep
import threading, gobject, os
from dispatcher import Dispatcher

# ####################################
# dispatcher
# example code:
#
#
# ####################################

class Thread(threading.Thread):

    def __init__(self, dispatcher, thread_num, length):
        threading.Thread.__init__(self)
        self.setDaemon(1)  # quit even if this thread is still running
        self.dispatcher = dispatcher
        self.thread_num = thread_num
        self.sleep_length = length

    def run(self):
        done = False
        print("thread_num = %s; process id = %d ****************" %(self.thread_num,os.getpid()))
        pid_func(self.thread_num)
        for num in range(250):
            #print self.thread_num, " num = ",num
            sleep(self.sleep_length)
            data = [ self.thread_num, (": time is slipping away: %d\n" %num), num, done]
            self.dispatcher(data) # signal main thread
        done = True
        data = [ self.thread_num, (": Time slipped away: I'm done"), num, done]
        self.dispatcher(data) # signal main thread


def pid_func(threadnum):
    print("pid_func: called from thread_num = %s; process id = %d ****************" %(threadnum,os.getpid()))

def message_fun(buffer, message):
    #print ("got a message : %s" %(message[0] + str(message[1])))
    if message[3]:
        thread_finished[message[0]] = True
        buffer.insert(buffer.get_end_iter(), message[0] + str(message[1]) + "\n\n")
    else:
        #message2 = ("%d x 3 = %d\n" %(message[2],message[2]*3))
        buffer.insert(buffer.get_end_iter(), message[0] + str(message[1])) # + message2)
    return

def timerfunc():
    if (not thread_finished["thread1"]) or (not thread_finished["thread2"]) \
                or (not thread_finished["thread3"]) or (not thread_finished["thread4"]):
        pbar.pulse()
        #print 'Plusing ProgressBar, since a thread is not finished'
        return True
    else:
        pbar.set_fraction(0)
        pbar.set_text("Done")
        return False

def on_window_map_event(event, param):
    print 'Window mapped'
    thread1 = Thread(Dispatcher(message_fun, buffer), "thread1", 0.9)
    thread2 = Thread(Dispatcher(message_fun, buffer), "thread2", 0.9)
    thread3 = Thread(Dispatcher(message_fun, buffer), "thread3", 0.9)
    thread4 = Thread(Dispatcher(message_fun, buffer), "thread4", 0.5)
    gobject.timeout_add(100, timerfunc)
    thread1.start()
    thread2.start()
    thread3.start()
    thread4.start()


if __name__ == "__main__":
       
    gtk.threads_init()
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    textview = gtk.TextView()
    buffer = textview.get_buffer()
    sw = gtk.ScrolledWindow()
    sw.add(textview)
    pbar = gtk.ProgressBar()
    vbox = gtk.VBox()
    vbox.pack_start(sw)
    vbox.pack_start(pbar, False)
    window.add(vbox)
    #gui_dispatcher = Dispatcher(message_fun, buffer)
    window.connect('map_event', on_window_map_event)
    window.connect("destroy", gtk.main_quit)
    window.resize(400, 600)
    window.show_all()
    thread_finished = {"thread1":False, "thread2":False, "thread3":False, "thread4":False}
    gtk.threads_enter()
    gtk.main()
    gtk.threads_leave()
