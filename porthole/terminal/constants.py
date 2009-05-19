#!/usr/bin/env python

"""
    ============
    | Terminal Constants |
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

"""

from gettext import gettext as _


# some constants for the tabs
TAB_PROCESS = 0
TAB_WARNING = 1
TAB_CAUTION = 2
TAB_INFO = 3
TAB_QUEUE = 4

# A constant that represents the maximum distance from the
# bottom of the slider for the slider to stick.  Too small and
# you won't be able to make it stick when text is added rapidly
SLIDER_CLOSE_ENOUGH = 0.5 # of the page size

TABS = [TAB_PROCESS, TAB_WARNING, TAB_CAUTION, TAB_INFO, TAB_QUEUE]


# some contant strings that can be internationalized except that gettext  or even dprint does not run at this point
# we do however need to mark them here anyway so they are included for translation
KILLED_STRING = _("*** process killed ***\n")
TERMINATED_STRING = _("*** process completed ***\n")
TAB_LABELS = [_("Process"), _("Warnings"), _("Cautions"), _("Summary"), _("Emerge queue")]

KILLED = -1
EXECUTE = 1
PAUSED = 0
FAILED = -2
COMPLETED = 2
PENDING = 3
