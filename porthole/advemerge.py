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
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
'''

import gtk, gtk.glade
from utils import load_web_page, dprint
from version import version

class AdvancedEmergeDialog:
    """Class to perform advanced emerge dialog functionality."""

    def __init__(self, prefs, package):
        # setup glade
        self.gladefile = prefs.DATA_PATH + "porthole.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "adv_emerge_dialog")
        self.package = package
        # register callbacks
        callbacks = {"on_adv_ok_clicked" : self.ok_clicked,
                     "on_adv_help_clicked" : self.help_clicked,
                     "on_adv_cancel_clicked" : self.cancel_clicked}
        self.wtree.signal_autoconnect(callbacks)
        self.window = self.wtree.get_widget("adv_emerge_dialog")
        self.window.set_title("Emerge Settings for " + package.full_name )
        self.combo = self.wtree.get_widget("clVersion")

        # Populate version dropdown list

        verList = [self.package.full_name] + self.package.get_versions()
        self.combo.set_popdown_strings(verList)


    def ok_clicked(self, widget):
        """ Interrogate object for settings and start the ebuild """
        # Build option string 

        options = self.get_options()

        # Build use flag string

        use_flags = ''
        if len(use_flags) > 0:
            use_flags = "USE='" + use_flags + "' "
        
        # Build accept keyword string

        accept_keywords = self.get_keyword()
        if len(accept_keywords) > 0:
            accept_keywords = "ACCEPT_KEYWORDS='" + accept_keywords + "' "

        # Send command to be processed

        print use_flags + \
            accept_keywords + \
            "emerge " + \
            options +\
            self.combo.entry.get_text()
        '''
        self.setup_command(package.get_name(), \
            use_flags + \
            accept_keywords + \
            "emerge " + \
            options +\
            self.combo.entry.get_text())
        '''

        # Dispose of the dialog!
        self.window.destroy()

    def cancel_clicked(self, widget):
        """Open Porthole's Homepage!"""
        self.window.destroy()


    def help_clicked(self, widget):
        """Open Porthole's Homepage!"""
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


    def get_options(self):
        """ Create keyword list from option checkboxes """
        List = [('cbBuildpkg', '-b ', '--buildpkg '),
                ('cbBuildPkgOnly', '-B ', '--buildpkgonly '),
                ('cbDebug', '-d ', '--debug '),
                ('cbFetchonly', '-f ', '--fetchonly '),
                ('cbEmptytree', '-e ', '--emptytree '),
                ('cbDeep', '-D ', '--deep '),
                ('cbNoconfmem', '--noconfmem ', '--noconfmem '),
                ('cbNodeps', '-O ', '--nodeps '),
                ('cbNoreplace', '-n ', '--noreplace '),
                ('cbOneshot', '--oneshot ', '--oneshot '),
                ('cbOnlydeps', '-o ', '--onlydeps '),
                ('cbPretend','-p ', '--pretend '),
                ('cbUpgradeonly','-U ', '--upgradeonly '),
                ('cbUpdate','-u ', '--update '),
                ('cbUsepkgonly', '-K ', '--usepkgonly '),
                ('cbUsepkg', '-k ', '--usepkg '),
                ('cbQuiet', '-q ', '--quiet '),
                ('cbVerbose', '-v ', '--verbose ')]
        options = ''
        for Name, ShortOption, LongOption in List:
            if self.wtree.get_widget(Name).get_active():
                options += LongOption
        return options
