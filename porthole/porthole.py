#!/usr/bin/env python

'''
    Porthole
    A graphical frontend to Portage

    Copyright (C) 2003 Fredrik Arnerup and Daniel G. Taylor

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

#set data path for our glade and pixmap files
DATA_PATH = "/usr/share/porthole/"

#store our version here
version = "0.1"

#setup our path so we can load our custom modules
from sys import path
path.append("/usr/lib/porthole")

from sys import argv, exit
from mainwindow import MainWindow
import gtk

if __name__ == "__main__":
    if len(argv) > 1:
        if(argv[1] == "--local" or argv[1] == "-l"):
            #running a local version (i.e. not installed in /usr/*)
            DATA_PATH = ""
        elif(argv[1] == "--version" or argv[1] == "-v"):
            #print version info
            print "Porthole " + version
            exit()
        else:
            print "Invalid argument passed"
            exit()
    #change dir to your data path
    if DATA_PATH:
        from os import chdir
        chdir(DATA_PATH)
    #make sure gtk lets threads run
    gtk.threads_init()
    #setup our app icon
    myicon = gtk.gdk.pixbuf_new_from_file("pixmaps/porthole-icon.png")
    gtk.window_set_default_icon_list(myicon)
    #create the main window
    myapp = MainWindow(version)
    #start the program loop
    gtk.mainloop()
