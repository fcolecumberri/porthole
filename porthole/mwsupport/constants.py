#!/usr/bin/env python

'''
    Porthole View Constants
    Support for the main interface views

    Copyright (C) 2003 - 2011
    Fredrik Arnerup, Brian Dolbec,
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
'''


from gettext import gettext as _


SHOW_ALL = 0
SHOW_INSTALLED = 1
SHOW_SEARCH = 2
SHOW_UPGRADE = 3
SHOW_DEPRECATED = 4
SHOW_SETS = 5

INDEX_TYPES = ["All", "Installed", "Search", "Upgradable", "Deprecated",
    "Sets", "Binpkgs"]

GROUP_SELECTABLE = [SHOW_UPGRADE, SHOW_DEPRECATED , SHOW_SETS]

ON = True
OFF = False

# create the translated reader type names
READER_NAMES = {"Deprecated": _("Deprecated"),
                "Sets": _("Sets"),
                "Upgradable": _("Upgradable"),
                "Binpkgs": _("Binpkgs")}

