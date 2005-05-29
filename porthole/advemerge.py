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
from utils import dprint
from version_sort import ver_sort
from loaders import load_web_page
from gettext import gettext as _

class AdvancedEmergeDialog:
    """Class to perform advanced emerge dialog functionality."""

    def __init__(self, prefs, package, setup_command):
        """ Initialize Advanced Emerge Dialog window """
        # Preserve passed parameters
        self.prefs = prefs
        self.package = package
        self.setup_command = setup_command
        self.arch = portagelib.get_arch()
        
        # Parse glade file
        self.gladefile = prefs.DATA_PATH + "advemerge-new.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "adv_emerge_dialog", self.prefs.APP)
     
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
                     "on_cmbVersion_changed" : self.version_changed,}

        self.wtree.signal_autoconnect(callbacks)
        self.window = self.wtree.get_widget("adv_emerge_dialog")
        self.window.set_title(_("Advanced Emerge Settings for ") + package.full_name)
        
        # Make tool tips available
        self.tooltips = gtk.Tooltips()
      
        # Build version combo list
        #self.combo = self.wtree.get_widget("cmbVersion")
        self.get_versions()
        

        # Build a formatted combo list from the versioninfo list 
        #comboList = []
        self.comboList = gtk.ListStore(str)
        index = 0
        for x in range(len(self.verList)):
            ver = self.verList[x]
            info = ver["number"]
            #info += '   [Slot:' + str(ver["slot"]) + ']'
            info += '   [' + _('Slot:%s' % ver["slot"]) + ']'
            if not ver["stable"]:
                info += _('   (unstable)')
            if ver["hard_masked"]:
                info += _('   [MASKED]')
            if ver["best"]:
                if ver["best_downgrades"]:
                    info += _('   (recommended) (downgrade)')
                else:
                    info += _('   (recommended)')
                index = x
            if ver["installed"]:
                info += _('   [installed]')
            #comboList.append(info)
        # put the recommended upgrade (or downgrade) at the top of the list
        #comboList.insert(0,comboList.pop(index))

        # Set the combo list
        #self.combo.set_popdown_strings(comboList)
            self.comboList.append([info])
        
        # Build version combobox
        self.combobox = self.wtree.get_widget("cmbVersion")
        self.combobox.set_model(self.comboList)
        cell = gtk.CellRendererText()
        self.combobox.pack_start(cell, gtk.TRUE)
        self.combobox.add_attribute(cell, 'text', 0)
        self.combobox.set_active(index) # select "recommended" ebuild by default
        #self.combobox.connect("changed",self.version_changed) # register callback
         
        # Set any emerge options the user wants defaulted
        if self.prefs.emerge.pretend:
            self.wtree.get_widget("cbPretend").set_active(True)
        if self.prefs.emerge.verbose:
            self.wtree.get_widget("cbVerbose").set_active(True)
        ## this now just references --update, which is probably not the desired behaviour.
        ## perhaps the current version should be indicated somewhere in the dialog
        #if self.prefs.emerge.upgradeonly:
        #    self.wtree.get_widget("cbUpgradeOnly").set_active(True)
        if self.prefs.emerge.fetch:
            self.wtree.get_widget("cbFetchOnly").set_active(True)

    #-----------------------------------------------
    # GUI Callback function definitions start here
    #-----------------------------------------------

    def ok_clicked(self, widget):
        """ Interrogate object for settings and start the ebuild """
        # Get selected version from combo list
        #sel_ver = self.combo.entry.get_text()
        iter = self.combobox.get_active_iter()
        model = self.combobox.get_model()
        sel_ver = model.get_value(iter, 0)

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
            '=' + verInfo["name"]

        # Dispose of the dialog
        self.window.destroy()
        
        # Submit the command for processing
        self.setup_command(self.package.get_name(), command)


    def cancel_clicked(self, widget):
        """ Cancel emerge """
        self.window.destroy()


    def help_clicked(self, widget):
        """ Display help file with web browser """
        load_web_page('file://' + self.prefs.DATA_PATH + 'help/advemerge.html')



    def version_changed(self, widget):
        """ Version has changed, update the dialog window """
        #sel_ver = self.combo.entry.get_text()
        dprint("ADVEMERGE: changing version")
        iter = self.combobox.get_active_iter()
        model = self.combobox.get_model()
        sel_ver = model.get_value(iter, 0)
        if len(sel_ver) > 2:
            verInfo = self.get_verInfo(sel_ver)
            # Reset use flags
            self.build_use_flag_widget(verInfo["use_flags"])
            # Reset keywords
            self.build_keywords_widget(verInfo["keywords"])


    def quiet_check(self, widget):
        """ If quiet is selected, disable verbose """
        if widget.get_active():
            self.wtree.get_widget("cbVerbose").set_active(False)


    def verbose_check(self, widget):
        """ If verbose is selected, disable quiet """
        if widget.get_active():
            self.wtree.get_widget("cbQuiet").set_active(False)


    def nodeps_check(self, widget):
        """ If nodeps is selected, disable onlydeps """
        if widget.get_active():
            self.wtree.get_widget("cbOnlyDeps").set_active(False)


    def onlydeps_check(self, widget):
        """ If onlydeps is selected, disable nodeps """
        if widget.get_active():
            self.wtree.get_widget("cbNoDeps").set_active(False)


    def buildpkg_check(self, widget):
        """ If buildpkg is selected, disable buildpkgonly """
        if widget.get_active():
            self.wtree.get_widget("cbBuildPkgOnly").set_active(False)


    def buildpkgonly_check(self, widget):
        """ If buildpkgonly is selected, disable buildpkg """
        if widget.get_active():
            self.wtree.get_widget("cbBuildPkg").set_active(False)


    def usepkg_check(self, widget):
        """ If usepkg is selected, disable usepkgonly """
        if widget.get_active():
            self.wtree.get_widget("cbUsePkgOnly").set_active(False)


    def usepkgonly_check(self, widget):
        """ If usepkgonly is selected, disable usepkg """
        if widget.get_active():
            self.wtree.get_widget("cbUsePkg").set_active(False)

    #------------------------------------------
    # Support function definitions start here
    #------------------------------------------

    def get_versions(self):
        """ Build a dictionary of all versions for this package
            with an info list for each version
 
            info["number"] = version number only
            info["name"] = full ebuild name
            info["best"] = True if best version for this system
            info["best_downgrades"] = True if "best" version will downgrade
            info["installed"] = True if installed
            info["slot"] = slot number
            info["keywords"] = keyword list
            info["use_flags"] = use flag list
            info["stable"] = True if stable on current architecture
            info["hard_masked"] = True if hard masked
        """ 
        self.verList = []
        # Get all versions sorted in chronological order
        ebuilds = ver_sort(self.package.get_versions())
 
        # Get all installed versions
        installed = self.package.get_installed()

        # get lists of hard masked and stable versions (unstable inferred)
        hardmasked = self.package.get_hard_masked(check_unmask = True)
        nonmasked = self.package.get_versions(include_masked = False)
        
        # iterate through ebuild list and create data structure
        for ebuild in ebuilds:
            # removed by Tommy:
            #~ props = self.package.get_properties(ebuild)
            #~ vernum = portagelib.get_version(ebuild)
            #~ isBest = ebuild == self.package.get_latest_ebuild()
            #~ isInstalled = ebuild in installed
            #~ slot = props.get_slot()
            #~ keywords = props.get_keywords()
            #~ useflags = props.get_use_flags()
            #~ # Append to list
            #~ self.verList.append([vernum, ebuild, isBest, isInstalled, slot, keywords, useflags])
            # added by Tommy:
            info = {}
            props = self.package.get_properties(ebuild)
            info["name"] = ebuild
            info["number"] = portagelib.get_version(ebuild)
            if ebuild in self.package.get_best_ebuild():
                info["best"] = True
                info["best_downgrades"] = ebuild not in portagelib.best(installed + [ebuild])
            else:
                info["best"] = info["best_downgrades"] = False
            info["installed"] = ebuild in installed
            info["slot"] = portagelib.get_property(ebuild, "SLOT")
            info["keywords"] = props.get_keywords()
            info["use_flags"] = props.get_use_flags()
            info["stable"] = ebuild in nonmasked
            info["hard_masked"] = ebuild in hardmasked
            self.verList.append(info)

    def get_verInfo(self, version):
        # Find selected version
        sel_ver = version.split(' ')[0]
        for x in range(len(self.verList)):
            ver = self.verList[x]
            if sel_ver == ver["number"]:
               verInfo = ver
               break
        if not verInfo:
            dprint("ADVEMERGE: get_verInfo(); freaking out! what's \"verInfo\"?")
            verInfo = "?"
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
        if maxrow < 1:
            maxrow = 1
        table = gtk.Table(maxrow, maxcol-1, True)
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
                button.set_active(True)
                self.ufList.append([button, '+' + flag])
            else:
                # Display unset flags with a -
                button = gtk.CheckButton('-' + flag)
                # By default they are set "off"
                button.set_active(False)
                self.ufList.append([button, '-' + flag])

            # Add tooltip, attach button to table and show it off
            # Use lower case flag, since that is how it is stored
            # in the UseFlagDict.  In case flag doesn't exist
            # we'll trap the error

            try:
                self.tooltips.set_tip(button, portagelib.UseFlagDict[flag.lower()][2])
            except KeyError:
                self.tooltips.set_tip(button, _('Unsupported use flag'))
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
        if maxrow < 1:
            maxrow = 1
        table = gtk.Table(maxrow, maxcol-1, True)
        KeywordsFrame.add(table)
        self.kwList = []

        # Iterate through use flags collection, create 
        # checkboxes and attach to table
        col = 0
        row = 0
        button = gtk.RadioButton(None, _('None'))
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
