#!/usr/bin/env python

'''
    Porthole Advanced Emerge Dialog
    Allows the user to set options, use flags, keywords and select
    specific versions.  Has lots of tool tips, too.

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

import gtk
import gtk.glade
import portagelib
import utils
from version_sort import ver_sort

class AdvancedEmergeDialog:
    """Class to perform advanced emerge dialog functionality."""

    def __init__(self, prefs, package, setup_command):
        """ Initialize Advanced Emerge Dialog window """
        # Preserve passed parameters
        self.prefs = prefs
        self.package = package
        self.setup_command = setup_command

        # Parse glade file
        self.gladefile = prefs.DATA_PATH + "advemerge.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "adv_emerge_dialog")
     
        # register callbacks
        callbacks = {"on_ok_clicked" : self.ok_clicked,
                     "on_help_clicked" : self.help_clicked,
                     "on_cancel_clicked" : self.cancel_clicked,
                     "on_cbOnlyDeps_clicked" : self.onlydeps_check,
                     "on_cbNoDeps_clicked" : self.nodeps_check,
                     "on_cbQuiet_clicked" : self.quiet_check,
                     "on_cbVerbose_clicked" : self.verbose_check,
                     "on_cbBuildPkg_clicked" : self.buildpkg_check,
                     "on_cbBuildPkgOnly_clicked" : self.buildpkgonly_check,
                     "on_cbUsePkg_clicked" : self.usepkg_check,
                     "on_cbUsePkgOnly_clicked" : self.usepkgonly_check,
                     "on_version_changed" : self.version_changed,}

        self.wtree.signal_autoconnect(callbacks)
        self.window = self.wtree.get_widget("adv_emerge_dialog")
        self.window.set_title("Advanced Emerge Settings for " + package.full_name)
        
        # Make tool tips available
        self.tooltips = gtk.Tooltips()
      
        # Build version combo list
        self.combo = self.wtree.get_widget("cmbVersion")
        self.get_versions()

        # Build a formatted combo list from the versioninfo list 
        comboList = []
        index = 0
        x = 0
        for ver in self.verList:
            info = ver[0]
            info += '   [Slot:' + str(ver[4]) + ']'
            if ver[2]:
                info += '   [best/latest]'
                index = x
            if ver[3]:
                info += '   [installed]'
            comboList.append(info)
            x += 1

        # Set the combo list
        self.combo.set_popdown_strings(comboList)
        
        # Set any emerge options the user wants defaulted
        if self.prefs.emerge.pretend:
            self.wtree.get_widget("cbPretend").set_active(gtk.TRUE)
        if self.prefs.emerge.verbose:
            self.wtree.get_widget("cbVerbose").set_active(gtk.TRUE)
        if not self.prefs.emerge.upgradeonly:
            self.wtree.get_widget("cbUpgradeOnly").set_active(gtk.TRUE)
        if self.prefs.emerge.fetch:
            self.wtree.get_widget("cbFetchOnly").set_active(gtk.TRUE)

    #-----------------------------------------------
    # GUI Callback function definitions start here
    #-----------------------------------------------

    def ok_clicked(self, widget):
        """ Interrogate object for settings and start the ebuild """
        # Get selected version from combo list
        sel_ver = self.combo.entry.get_text()

        # Get version info of selected version
        verInfo = self.get_verInfo(sel_ver)

        # Build use flag string
        use_flags = self.get_use_flags()
        if len(use_flags) > 0:
            use_flags = "USE='" + use_flags + "' "
        
        # Build accept keyword string
        accept_keyword = self.get_keyword()
        if len(accept_keyword) > 0:
            accept_keyword = "ACCEPT_KEYWORDS='" + accept_keyword + "' "

        # Send command to be processed
        command = use_flags + \
            accept_keyword + \
            "emerge " + \
            self.get_options() + \
            '=' + verInfo[1]

        # Dispose of the dialog
        self.window.destroy()
        
        # Submit the command for processing
        self.setup_command(self.package.get_name(), command)


    def cancel_clicked(self, widget):
        """ Cancel emerge """
        self.window.destroy()


    def help_clicked(self, widget):
        """ Display help file with web browser """
        utils.load_web_page('file://' + self.prefs.DATA_PATH + 'help/advemerge.html')



    def version_changed(self, widget):
        """ Version has changed, update the dialog window """
        sel_ver = self.combo.entry.get_text()
        if len(sel_ver) > 2:
            verInfo = self.get_verInfo(sel_ver)
            # Reset use flags
            self.build_use_flag_widget(verInfo[6])
            # Reset keywords
            self.build_keywords_widget(verInfo[5])


    def quiet_check(self, widget):
        """ If quiet is selected, disable verbose """
        if widget.get_active():
            self.wtree.get_widget("cbVerbose").set_active(gtk.FALSE)


    def verbose_check(self, widget):
        """ If verbose is selected, disable quiet """
        if widget.get_active():
            self.wtree.get_widget("cbQuiet").set_active(gtk.FALSE)


    def nodeps_check(self, widget):
        """ If nodeps is selected, disable onlydeps """
        if widget.get_active():
            self.wtree.get_widget("cbOnlyDeps").set_active(gtk.FALSE)


    def onlydeps_check(self, widget):
        """ If onlydeps is selected, disable nodeps """
        if widget.get_active():
            self.wtree.get_widget("cbNoDeps").set_active(gtk.FALSE)


    def buildpkg_check(self, widget):
        """ If buildpkg is selected, disable buildpkgonly """
        if widget.get_active():
            self.wtree.get_widget("cbBuildPkgOnly").set_active(gtk.FALSE)


    def buildpkgonly_check(self, widget):
        """ If buildpkgonly is selected, disable buildpkg """
        if widget.get_active():
            self.wtree.get_widget("cbBuildPkg").set_active(gtk.FALSE)


    def usepkg_check(self, widget):
        """ If usepkg is selected, disable usepkgonly """
        if widget.get_active():
            self.wtree.get_widget("cbUsePkgOnly").set_active(gtk.FALSE)


    def usepkgonly_check(self, widget):
        """ If usepkgonly is selected, disable usepkg """
        if widget.get_active():
            self.wtree.get_widget("cbUsePkg").set_active(gtk.FALSE)

    #------------------------------------------
    # Support function definitions start here
    #------------------------------------------

    def get_versions(self):
        """ Build a list of all versions for this package
            with an info list for each version
 
            info[0] = version number only
            info[1] = full ebuild name
            info[2] = is best (latest) version
            info[3] = is installed
            info[4] = slot
            info[5] = keyword list
            info[6] = use flag list
        """ 
        self.verList = []
        # Get all versions sorted in chronological order
        ebuilds = ver_sort(self.package.get_versions())
 
        # Get all installed versions
        installed = self.package.get_installed()

        # iterate through ebuild list and create data structure
        for ebuild in ebuilds:
            props = self.package.get_properties(ebuild)
            vernum = portagelib.get_version(ebuild)
            isBest = ebuild == self.package.get_latest_ebuild()
            isInstalled = ebuild in installed
            slot = props.get_slot()
            keywords = props.get_keywords()
            useflags = props.get_use_flags()
            # Append to list
            self.verList.append([vernum, ebuild, isBest, isInstalled, slot, keywords, useflags])
 

    def get_verInfo(self, version):
        # Find selected version
        sel_ver = version.split(' ')[0]
        for ver in self.verList:
            if sel_ver == ver[0]:
               verInfo = ver
               break
        return verInfo


    def get_keyword(self):
        """ Get keyword selected by user """
        keyword = ''
        for item in self.kwList:
            keyword = item[1]
            if item[0].get_active():
                return keyword.strip()
        return ''


    def get_use_flags(self):
        """ Get use flags selected by user """
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


    def build_use_flag_widget(self, use_flags):
        """ Create a table layout and populate it with 
            checkbox widgets representing the available
            use flags
        """
        UseFlagFrame = self.wtree.get_widget("frameUseFlags")
        # If frame has any children, remove them
        child = UseFlagFrame.child
        if child != None:
            UseFlagFrame.remove(child)

        # Build table to hold checkboxes
        size = len(use_flags)
        maxcol = 3
        maxrow = size / maxcol - 1
        if maxrow < 0:
            maxrow = 0
        table = gtk.Table(maxrow, maxcol-1, gtk.TRUE)
        UseFlagFrame.add(table)

        self.ufList = []

        # Iterate through use flags collection, create checkboxes
        # and attach to table
        col = 0
        row = 0
        for flag in use_flags:
            
            button = gtk.CheckButton(flag)
            if flag in portagelib.SystemUseFlags:
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

            # Add tooltip, attach button to table and show it off
            # Use lower case flag, since that is how it is stored
            # in the UseFlagDict.  In case flag doesn't exist
            # we'll trap the error

            try:
                self.tooltips.set_tip(button, portagelib.UseFlagDict[flag.lower()][2])
            except KeyError:
                self.tooltips.set_tip(button, 'Unsupported use flag')
            table.attach(button, col, col+1, row, row+1)
            button.show()
            # Increment col & row counters
            col += 1
            if col > maxcol:
                col = 0
                row += 1

        # Display the entire table
        table.show()


    def build_keywords_widget(self, keywords):
        """ Create a table layout and populate it with 
            checkbox widgets representing the available
            keywords
        """
        KeywordsFrame = self.wtree.get_widget("frameKeywords")

        # If frame has any children, remove them
        child = KeywordsFrame.child
        if child != None:
            KeywordsFrame.remove(child)

        # Build table to hold radiobuttons
        size = len(keywords) + 1  # Add one for None button
        maxcol = 5
        maxrow = size / maxcol - 1
        if maxrow < 0:
            maxrow = 0
        table = gtk.Table(maxrow, maxcol-1, gtk.TRUE)
        KeywordsFrame.add(table)
        self.kwList = []

        # Iterate through use flags collection, create 
        # checkboxes and attach to table
        col = 0
        row = 0
        button = gtk.RadioButton(None, 'None')
        rbGroup = button
        table.attach(button, col, col+1, row, row+1)
        button.show()
        col += 1
        for keyword in keywords:
            if keyword[0] == '~':
                button = gtk.RadioButton(rbGroup, keyword)
                self.kwList.append([button, keyword])
                table.attach(button, col, col+1, row, row+1)
                button.show()
            else:
                label = gtk.Label(keyword)
                label.set_alignment(.05, .5)
                table.attach(label, col, col+1, row, row+1)
                label.show()
            # Increment col & row counters
            col += 1
            if col > maxcol:
                col = 0
                row += 1
        # Display the entire table
        table.show()
