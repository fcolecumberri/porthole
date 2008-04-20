#!/usr/bin/env python

"""
    ============
    | Terminal |
    -----------------------------------------------------------
    A graphical process output viewer/filter and emerge queue
    -----------------------------------------------------------
    Copyright (C) 2003 - 2008 Fredrik Arnerup, Brian Dolbec, 
    Daniel G. Taylor, Wm. F. Wheeler, Tommy Iorns

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

        def callback():
            print "This is called when a process finishes"

        manager = ProcessManager(environment, preferences)
        manager.add(package_name, command_to_run, callback)
        ...
    -------------------------------------------------------------------------
    References & Notes
    
    1. Pygtk2 refs & tutorials - http://www.pygtk.org
    2. GTK2 text tags can use named colors (see /usr/X11R6/lib/X11/rgb.txt)
       or standard internet rgb values (e.g. #02FF80)
 
"""
