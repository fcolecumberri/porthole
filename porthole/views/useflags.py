#!/usr/bin/env python

import datetime
_id = datetime.datetime.now().microsecond
import gtk
import gtk.glade
from gtk.gdk import Event, WINDOW_STATE

from porthole.utils import utils
from porthole.utils import debug
from porthole import backends
from porthole import config
from porthole import db
portage_lib = backends.portage_lib
from porthole.backends.utilities import (get_reduced_flags, abs_list,
        abs_flag, filter_flags)


class UseFlagWidget(gtk.Table):
   def __init__(self, use_flags, ebuild):
      gtk.Widget.__init__(self)
      self.ebuild = ebuild
      debug.dprint("USEFLAGDIALOG: __INIT__()")
      size = len(use_flags)
      maxcol = 3
      maxrow = (size-1) / (maxcol+1)
      table = gtk.Table(maxrow+2, maxcol+1, True)
      if maxrow+1 >= 6:
         scrolledwindow = gtk.ScrolledWindow()
         scrolledwindow.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
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
         flag_active = False
         myflag = abs_flag(flag)
         if myflag in ebuild_use_flags:
            flag_active = True
         button = gtk.CheckButton(flag)
         button.set_use_underline=(False)
         button.set_active(flag_active)
         self.ufList.append([button,flag])

         button.set_has_tooltip=(True)
         try:
            button.set_tooltip_text(portage_lib.settings.UseFlagDict[flag.lower()][2])
         except KeyError:
            button.set_tooltip_text(_('Unsupported use flag'))
         table.attach(button, col, col+1, row, row+1)
         #connect to on_toggled so we can show changes
         button.connect("toggled", self.on_toggled)
         button.show()
         #increment column and row
         col+=1
         if col > maxcol:
            col = 0
            row += 1
      table.show()
      self.show()

   def get_use_flags(self, ebuild=None):
      flaglist = []
      if ebuild is None:
         ebuild_use_flags = get_reduced_flags(self.ebuild)
      else:
         ebuild_use_flags = get_reduced_flags(ebuild)
      for child in self.ufList:
         flag = child[1]
         if flag in ebuild_use_flags:
            flag_active = True
         else:
            flag_active = False
         if child[0].get_active():
            if not flag_active:
               flaglist.append(flag)
         else:
            if flag_active:
               flaglist.append('-' + flag)
      flags = ' '.join(flaglist)
      debug.dprint("USEFLAGS: get_use_flags(); flags = %s" %str(flags))
      return flags

   def save_use(self, widget):
      debug.dprint("USEFLAGS: saveConf()")
      use_flags = self.get_use_flags()
      if not use_flags:
         return
      addlist = use_flags.split()
      removelist =[]
      for item in addlist:
         if item.startswith('-'):
            removelist.append(item[1:])
         else:
            removelist.append('-' + item)
      db.userconfigs.set_user_config('USE', '', self.ebuild,add=addlist ,
            remove=removelist, callback=self.on_toggled, parent_window=self.window)

   def on_toggled(self, widget):
      #self.set_focus_child(widget)
      self.emit('grab-focus')
