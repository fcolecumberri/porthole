#!/usr/bin/env python

'''
    Porthole Views sorts.py
    The treeview column sort functions

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
from porthole.packagebook.depends import DependsTree
#from porthole.utils import debug
from porthole.views.helpers import *

def size_sort_func(treemodel, iter1, iter2):
    """Sorts by download size"""
    text1 = treemodel.get_value(iter1, 6)
    text2 = treemodel.get_value(iter2, 6)
    try: size1 = int(text1[:-3].replace(',', ''))
    except:
        try: size2 = int(text2[:-3].replace(',', ''))
        except: return 0
        return 1
    try: size2 = int(text2[:-3].replace(',', ''))
    except: return -1
    if size2 > size1: return 1
    if size2 < size1: return -1
    return 0

def latest_sort_func(treemodel, iter1, iter2):
    """Sorts by the difference between the installed and recommended versions"""
    installed1 = treemodel.get_value(iter1, 7)
    installed2 = treemodel.get_value(iter2, 7)
    latest1 = treemodel.get_value(iter1, 8)
    latest2 = treemodel.get_value(iter2, 8)
    if not installed1 or not latest1:
        if not installed2 or not latest2:
            return 0
        return 1
    if not installed2 or not latest2: return -1
    lsplit1 = latest1.split('.')
    lsplit2 = latest2.split('.')
    isplit1 = installed1.split('.')
    isplit2 = installed2.split('.')
    dlist1 = []
    for x in range(min(len(lsplit1), len(isplit1))):
        try: diff = int(lsplit1[x]) - int(isplit1[x])
        except: break
        dlist1.append(diff)
    dlist2 = []
    for x in range(min(len(lsplit2), len(isplit2))):
        try: diff = int(lsplit2[x]) - int(isplit2[x])
        except: break
        dlist2.append(diff)
    for x in range(max(len(dlist1), len(dlist2))):
        if x == len(dlist1): dlist1.append(0)
        if x == len(dlist2): dlist2.append(0)
        if dlist1[x] > dlist2[x]: return -1
        if dlist1[x] < dlist2[x]: return 1
    return 0

def installed_sort_func(treemodel, iter1, iter2):
    """Currently just puts installed packages at the top,
    with world packages above deps"""
    inst1 = treemodel.get_value(iter1, 7)
    inst2 = treemodel.get_value(iter2, 7)
    if not inst1:
        if not inst2:
            return package_sort_func(treemodel, iter1, iter2)
        return 1
    if not inst2:
        return -1
    if treemodel.get_value(iter1, 4): # True if in world file
        if treemodel.get_value(iter2, 4):
            return package_sort_func(treemodel, iter1, iter2)
        return -1
    if treemodel.get_value(iter2, 4):
        return 1
    return package_sort_func(treemodel, iter1, iter2)

def package_sort_func(treemodel, iter1, iter2):
    """Sorts alphabetically by package name"""
    name1 = treemodel.get_value(iter1, 0)
    name2 = treemodel.get_value(iter2, 0)
    if name1 > name2: return 1
    if name2 > name1: return -1
    return 0
