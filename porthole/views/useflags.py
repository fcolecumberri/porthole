#!/usr/bin/env python

import datetime
_id = datetime.datetime.now().microsecond
from gi.repository import GObject
from gi.repository import Gtk

from gettext import gettext as _

from porthole.utils import debug
from porthole import backends
from porthole.backends.utilities import (get_reduced_flags,
        abs_flag, )


class UseFlagCheckbuttons(Gtk.HBox):
   def __init__(self, useflag, default_status):
      Gtk.HBox.__init__(self)
      debug.dprint("USEFLAGCHECKBUTTONS: __INIT__()")
      self.homogenous = False # Not all widgets are created equal
      self.flag = useflag

      self.enable_box = Gtk.CheckButton("+")
      self.enable_box.connect('toggled', self.set_enabled)
      self.enable_box.show()

      self.disable_box = Gtk.CheckButton("-")
      self.disable_box.connect('toggled', self.set_disabled)
      self.disable_box.show()

      flag_label = Gtk.Label(label=useflag + "(" + default_status + ")")
      flag_label.show()

      self.pack_start(self.enable_box, expand=False, fill=False, padding=0)
      self.pack_start(self.disable_box, expand=False, fill=False, padding=0)
      self.pack_start(flag_label, expand=False, fill=False, padding=0)

   def set_enabled(self, widget=None):
      debug.dprint("USEFLAGS: set_enabled()")
      if widget != None:
         if widget.get_active():
            self.disable_box.set_active(False)
      self.emit('grab-focus')

   def set_disabled(self, widget=None):
      debug.dprint("USEFLAGS: set_disabled()")
      if widget != None:
        if widget.get_active():
            self.enable_box.set_active(False)
      self.emit('grab-focus')

   def get_flag(self):
      if self.enable_box.get_active():
         return "+" + self.flag
      elif self.disable_box.get_active():
         return "-" + self.flag
      return self.flag

class UseFlagWidget(Gtk.Table):
   def __init__(self, use_flags, ebuild, parent_window):
      GObject.GObject.__init__(self)
      self.ebuild = ebuild
      self.parent_window = parent_window
      debug.dprint("USEFLAGDIALOG: __INIT__()")

      size = len(use_flags)
      maxcol = 3
      maxrow = (size-1) / (maxcol+1)
      table = Gtk.Table(maxrow+2, maxcol+1, True)
      if maxrow+1 >= 6:
         scrolledwindow = Gtk.ScrolledWindow()
         scrolledwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
         self.add(scrolledwindow)
         scrolledwindow.add_with_viewport(table)
         scrolledwindow.set_size_request(1,100)
         scrolledwindow.show()
      else:
         self.add(table)

      self.ufList = []

      col = 0
      row = 0
      ebuild_use_flags = get_reduced_flags(ebuild)

      for flag in use_flags:
         if flag[0] == '-':
               button = UseFlagCheckbuttons(flag[1:], "-")
         elif flag[0] == '+':
               button = UseFlagCheckbuttons(flag[1:], "+")
         else:
               button = UseFlagCheckbuttons(flag, "")
         myflag = abs_flag(flag)
         if flag in ebuild_use_flags:
            button.enable_box.set_active(True)
         if flag[0] == '-':
               button.disable_box.set_active(True)
         elif flag[0] == '+':
               button.disable_box.set_active(False)
         self.ufList.append([button, flag])

         button.set_has_tooltip=True
         try:
            button.set_tooltip_text(backends.portage_lib.settings.UseFlagDict[myflag.lower()][2])
         except KeyError:
            button.set_tooltip_text(_('Unsupported use flag'))
         table.attach(button, col, col+1, row, row+1)
         #connect to grab-focus so we can detect changes
         button.connect('grab-focus', self.on_toggled)
         button.show()
         #increment column and row
         col+=1
         if col > maxcol:
            col = 0
            row += 1
      table.show()
      self.show()

   def get_use_flags(self, ebuild=None):
      debug.dprint("USEFLAGS: get_use_flags()")
      flaglist = []
      if ebuild is None:
         ebuild_use_flags = get_reduced_flags(self.ebuild)
      else:
         ebuild_use_flags = get_reduced_flags(ebuild)
      for child in self.ufList:
         #flag = child[1]
         flag = child[0].get_flag()
         #base_flag = abs_flag(flag)
         if flag[0] == '+':
            if not flag[1:] in ebuild_use_flags:
                  flaglist.append(flag)
         elif flag[0] == '-':
            if not flag in ebuild_use_flags:
                flaglist.append(flag)
      flags = ' '.join(flaglist)
      debug.dprint("USEFLAGS: get_use_flags(); flags = %s" %str(flags))
      return flags

   def on_toggled(self, widget):
      self.emit('grab-focus')
