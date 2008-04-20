#!/usr/bin/env python

'''
    Porthole Views
    The view menu classes

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

import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, gobject, pango
import threading, os
from gettext import gettext as _

from porthole.utils import utils
from porthole import backends
portage_lib = backends.portage_lib
from porthole.packagebook.depends import DependsTree
from porthole.utils import debug
from porthole.views.helpers import *


class RMBMenu:
    """ Common right mouse button menu for views
    """

    def __init__(self):
        # create popup menu for rmb-click
        arch = "~" + portage_lib.get_arch()
        menu = gtk.Menu()
        menuitems = {}
        menuitems["emerge"] = gtk.MenuItem(_("Emerge"))
        menuitems["emerge"].connect("activate", self.emerge)
        menuitems["pretend-emerge"] = gtk.MenuItem(_("Pretend Emerge"))
        menuitems["pretend-emerge"].connect("activate", self.emerge, True, None)
        menuitems["sudo-emerge"] = gtk.MenuItem(_("Sudo Emerge"))
        menuitems["sudo-emerge"].connect("activate", self.emerge, None, True)
        menuitems["unmerge"] = gtk.MenuItem(_("Unmerge"))
        menuitems["unmerge"].connect("activate", self.unmerge)
        menuitems["sudo-unmerge"] = gtk.MenuItem(_("Sudo Unmerge"))
        menuitems["sudo-unmerge"].connect("activate", self.unmerge, True)
        menuitems["add-keyword"] = gtk.MenuItem(_("Append with %s to package.keywords") % arch)
        menuitems["add-keyword"].connect("activate", self.add_keyword)
        menuitems["deselect_all"] = gtk.MenuItem(_("De-Select all"))
        menuitems["deselect_all"].connect("activate", self.deselect_all)
        menuitems["select_all"] = gtk.MenuItem(_("Select all"))
        menuitems["select_all"].connect("activate", self.select_all)
        
        for item in menuitems.values():
            menu.append(item)
            item.show()

        self.popup_menu = menu
        self.popup_menuitems = menuitems


    def _clicked(self, treeview, *args):
        """ Handles treeview clicks """
        debug.dprint("VIEWS: Package view _clicked() signal caught")
        # get the selection
        package = utils.get_treeview_selection(treeview, 2)
        #debug.dprint("VIEWS: package = %s" % package.full_name)

        #pop up menu if was rmb-click
        if self.dopopup:
            if utils.utils.is_root():
                if package.get_best_ebuild() != package.get_latest_ebuild(): # i.e. no ~arch keyword
                    self.popup_menuitems["add-keyword"].show()
                else: self.popup_menuitems["add-keyword"].hide()
                installed = package.get_installed()
                havebest = False
                if installed:
                    self.popup_menuitems["unmerge"].show()
                    if package.get_best_ebuild() in installed:
                        havebest = True
                else:
                    self.popup_menuitems["unmerge"].hide()
                if havebest:
                    self.popup_menuitems["emerge"].hide()
                    self.popup_menuitems["pretend-emerge"].hide()
                else:
                    self.popup_menuitems["emerge"].show()
                    self.popup_menuitems["pretend-emerge"].show()
                self.popup_menuitems["sudo-emerge"].hide()
                self.popup_menuitems["sudo-unmerge"].hide()
            else:
                self.popup_menuitems["emerge"].hide()
                self.popup_menuitems["unmerge"].hide()
                if utils.can_gksu() and \
                        (package.get_best_ebuild() != package.get_latest_ebuild()):
                    self.popup_menuitems["add-keyword"].show()
                else:
                    self.popup_menuitems["add-keyword"].hide()
                installed = package.get_installed()
                havebest = False
                if installed and utils.can_sudo():
                    self.popup_menuitems["sudo-unmerge"].show()
                    if package.get_best_ebuild() in installed:
                        havebest = True
                else:
                    self.popup_menuitems["sudo-unmerge"].hide()
                if havebest:
                    self.popup_menuitems["sudo-emerge"].hide()
                    self.popup_menuitems["pretend-emerge"].hide()
                else:
                    if utils.can_sudo():
                        self.popup_menuitems["sudo-emerge"].show()
                    else:
                        self.popup_menuitems["sudo-emerge"].hide()
                    self.popup_menuitems["pretend-emerge"].show()
            self.popup_menu.popup(None, None, None, self.event.button, self.event.time)
            self.dopopup = False
            self.event = None
            return True
 
