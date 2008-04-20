#!/usr/bin/env python

'''
    Porthole Views/helpers
    The view helper functions

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor, Brian Dolbec,
    Brian Bockelman, Tommy Iorns

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

from porthole.utils import debug

# establish some modules global variables
mainwindow_callback = None

def register_callbacks(self, callback = None):
    """ Callback to MainWindow.
        Currently takes an action and possibly one argument and passes it or them
        back to the function specified when MainWindow called register_callbacks.
        Actions can be "emerge", "emerge pretend", "unmerge", "set path",
        "package changed" or "refresh".
    """
    global mainwindow_callback
    mainwindow_callback = callback

def add_keyword(self, widget):
    arch = "~" + _portage_lib.get_arch()
    name = utils.get_treeview_selection(self, 2).full_name
    string = name + " " + arch + "\n"
    debug.dprint("VIEWS: Package view add_keyword(); %s" %string)
    def callback():
        global mainwindow_callback
        mainwindow_callback("refresh")
    _portage_lib.set_user_config('package.keywords', name=name, add=arch, callback=callback)
    #package = utils.get_treeview_selection(self,2)
    #package.best_ebuild = package.get_latest_ebuild()
    #mainwindow_callback("refresh")

def emerge(self, widget, pretend=None, sudo=None):
    emergestring = 'emerge'
    if pretend:
        #mainwindow_callback("emerge pretend")
        #return
        emergestring += ' pretend'
    #else:
        #   mainwindow_callback("emerge")
    if sudo:
        emergestring += ' sudo'
    global mainwindow_callback
    mainwindow_callback(emergestring)

def unmerge(self, widget, sudo=None):
    global mainwindow_callback
    if sudo:
        mainwindow_callback("unmerge sudo")
    else:
        mainwindow_callback("unmerge")

