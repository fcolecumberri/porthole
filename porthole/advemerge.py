#!/usr/bin/env python

'''
    Porthole Advanced Emerge Dialog
    Allows the user to set options, use flags and keywords

    Copyright (C) 2003 - 2004 Fredrik Arnerup, Daniel G. Taylor, Brian Dolbec 
    and Wm. F. Wheeler

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See thefor index in range(1,len(
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
'''

import gtk, gtk.glade
import portagelib
from version_sort import ver_sort
from utils import load_web_page, dprint
from version import version

class AdvancedEmergeDialog:
    """Class to perform advanced emerge dialog functionality."""

    def __init__(self, prefs, package, setup_command):
        """ Initialize Advanced Emerge Dialog window """
        self.prefs = prefs
        # setup glade
        self.gladefile = prefs.DATA_PATH + "advemerge.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "adv_emerge_dialog")
        self.package = package
        self.setup_command = setup_command
        # register callbacks
        callbacks = {"on_ok_clicked" : self.ok_clicked,
                     "on_help_clicked" : self.help_clicked,
                     "on_cancel_clicked" : self.cancel_clicked,
                     "on_cbQuiet_clicked" : self.quiet_check,
                     "on_cbVerbose_clicked" : self.verbose_check}

        self.wtree.signal_autoconnect(callbacks)
        self.window = self.wtree.get_widget("adv_emerge_dialog")
        self.window.set_title("Emerge Parameters for " + package.full_name )
        self.combo = self.wtree.get_widget("clVersion")

        # Set up use flag info

        self.UseFlagFrame = self.wtree.get_widget("frameUseFlags")
        self.sys_use_flags = portagelib.get_portage_environ("USE").split()
        self.ufList = []
        self.build_use_flag_widget()
      
        # Populate version dropdown list

        verList = [self.package.full_name] + \
            ver_sort(self.package.get_versions())

        # Insert equal sign into explicit versions for 
        # proper emerge operation
        for index in range(1,len(verList)):
            verList[index] = '=' + verList[index]

        self.combo.set_popdown_strings(verList)


    def ok_clicked(self, widget):
        """ Interrogate object for settings and start the ebuild """
        # Build use flag string
        use_flags = self.get_use_flags()
        if len(use_flags) > 0:
            use_flags = "USE='" + use_flags + "' "
        
        # Build accept keyword string
        accept_keywords = self.get_keyword()
        if len(accept_keywords) > 0:
            accept_keywords = "ACCEPT_KEYWORDS='" + accept_keywords + "' "

        # Send command to be processed
        command = use_flags + \
            accept_keywords + \
            "emerge " + \
            self.get_options() + \
            self.combo.entry.get_text()

        # Dispose of the dialog
        self.window.destroy()
        
        # Submit the command for processing
        self.setup_command(self.package.get_name(), command)

    def cancel_clicked(self, widget):
        """ Cancel operation """
        self.window.destroy()

    def help_clicked(self, widget):
        """ Display help (someday) """
        self.window.destroy()

    def get_keyword(self):
        """ Create keyword list from radio buttons """
        List = [('rbKW_None',''),
                 ('rbKW_X86','~x86'),
                 ('rbKW_PPC','~ppc'),
                 ('rbKW_Sparc','~sparc'),
                 ('rbKW_MIPS','~mips'),
                 ('rbKW_Alpha','~alpha'),
                 ('rbKW_ARM','~arm'),
                 ('rbKW_HPPA','~hppa')]

        for Name, KeyWord in List:
            if self.wtree.get_widget(Name).get_active():
                return KeyWord
        return ''

    def get_use_flags(self):
        flags = ''
        for child in self.ufList:
            flag = child[1][1:]
            if child[0].get_active():
                if child[1][0] == '-':
                    flags += flag + ' '
            else:
                if child[1][0] == '+':
                    flags += '-' + flag + ' '
        return flags

    def get_options(self):
        """ Create keyword list from option checkboxes """
        List = [('cbBuildPkg', '-b ', '--buildpkg '),
                ('cbBuildPkgOnly', '-B ', '--buildpkgonly '),
                ('cbDebug', '-d ', '--debug '),
                ('cbFetchOnly', '-f ', '--fetchonly '),
                ('cbEmptyTree', '-e ', '--emptytree '),
                ('cbDeep', '-D ', '--deep '),
                ('cbNoConfMem', '--noconfmem ', '--noconfmem '),
                ('cbNoDeps', '-O ', '--nodeps '),
                ('cbNoReplace', '-n ', '--noreplace '),
                ('cbOneShot', '--oneshot ', '--oneshot '),
                ('cbOnlyDeps', '-o ', '--onlydeps '),
                ('cbPretend','-p ', '--pretend '),
                ('cbUpgradeOnly','-U ', '--upgradeonly '),
                ('cbUpdate','-u ', '--update '),
                ('cbUsePkgOnly', '-K ', '--usepkgonly '),
                ('cbUsePkg', '-k ', '--usepkg '),
                ('cbQuiet', '-q ', '--quiet '),
                ('cbVerbose', '-v ', '--verbose ')]
        options = ''
        for Name, ShortOption, LongOption in List:
            if self.wtree.get_widget(Name).get_active():
                options += LongOption
        if self.prefs.emerge.nospinner:
            options += '--nospinner '
        return options

    def quiet_check(self, widget):
        """ If quiet is selected, disable verbose """
        if widget.get_active():
            self.wtree.get_widget("cbVerbose").set_active(gtk.FALSE)

    def verbose_check(self, widget):
        """ If verbose is selected, disable quiet """
        if widget.get_active():
            self.wtree.get_widget("cbQuiet").set_active(gtk.FALSE)

    def build_use_flag_widget(self):
        """ Create a table layout and populate it with 
            checkbox widgets representing the available
            use flags
        """
        # Get package use flags
        props = self.package.get_properties()
        use_flags = props.get_use_flags()

        # Build table to hold checkboxes
        size = len(use_flags)
        maxcol = 3
        maxrow = size / maxcol - 1
        if maxrow < 0:
            maxrow = 0
        table = gtk.Table(maxrow, maxcol-1, gtk.TRUE)
        self.UseFlagFrame.add(table)

        self.ufList = []

        # Iterate through use flags collection, create checkboxes
        # and attach to table
        col = 0
        row = 0
        for flag in use_flags:
            
            button = gtk.CheckButton(flag)
            if flag in self.sys_use_flags:
                # Display system level flags with a +
                button = gtk.CheckButton('+' + flag)
                # By default they are set "on"
                button.set_active(gtk.TRUE)
                self.ufList.append([button, '+' + flag])
            else:
                # Display unset flags with a -
                button = gtk.CheckButton('-' + flag)
                # By default they are set "off"
                button.set_active(gtk.FALSE)
                self.ufList.append([button, '-' + flag])
            # Attach button to table and show it
            table.attach(button, col, col+1, row, row+1)
            button.show()
            # Increment col & row counters
            col += 1
            if col > maxcol:
                col = 0
                row += 1
        # Display the entire table
        table.show()

