#!/usr/bin/env python

'''
    Porthole Advanced Emerge Dialog
    Allows the user to set options, use flags, keywords and select
    specific versions.  Has lots of tool tips, too.

    Copyright (C) 2003 - 2005 Fredrik Arnerup, Daniel G. Taylor, Brian Dolbec, 
    Wm. F. Wheeler and Tommy Iorns

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
from dispatcher import Dispatcher
from gettext import gettext as _

class AdvancedEmergeDialog:
    """Class to perform advanced emerge dialog functionality."""

    def __init__(self, prefs, package, setup_command, re_init_portage):
        """ Initialize Advanced Emerge Dialog window """
        # Preserve passed parameters
        self.prefs = prefs
        self.package = package
        self.setup_command = setup_command
        self.re_init_portage = re_init_portage
        self.arch = portagelib.get_arch()
        self.system_use_flags = portagelib.SystemUseFlags
        self.emerge_unmerge = "emerge"
        self.is_root = utils.is_root()
        self.package_use_flags = portagelib.get_user_config('package.use', package.full_name)
        self.current_verInfo = None
        
        # Parse glade file
        self.gladefile = prefs.DATA_PATH + "advemerge.glade"
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
                     "on_cmbVersion_changed" : self.version_changed,
                     "on_cmbEmerge_changed" : self.emerge_changed,
                     "on_btnPkgUse_clicked" : self.on_package_use_commit,
                     "on_btnMakeConf_clicked" : self.on_make_conf_commit,
                     "on_btnPkgKeywords_clicked" : self.on_package_keywords_commit,
        }
        
        self.wtree.signal_autoconnect(callbacks)
        self.window = self.wtree.get_widget("adv_emerge_dialog")
        self.use_flags_frame = self.wtree.get_widget("frameUseFlags")
        self.keywords_frame = self.wtree.get_widget("frameKeywords")
        self.window.set_title(_("Advanced Emerge Settings for %s") % package.full_name)
        
        self.command_textview = self.wtree.get_widget("command_textview")
        self.command_buffer = self.command_textview.get_buffer()
        style = self.keywords_frame.get_style().copy()
        self.bgcolor = style.bg[gtk.STATE_NORMAL]
        self.command_textview.modify_base(gtk.STATE_NORMAL, self.bgcolor)
        
        self.btnMakeConf = self.wtree.get_widget("btnMakeConf")
        self.btnPkgUse = self.wtree.get_widget("btnPkgUse")
        self.btnPkgKeywords = self.wtree.get_widget("btnPkgKeywords")
        if not (self.is_root or utils.can_gksu()):
            self.btnMakeConf.hide()
            self.btnPkgUse.hide()
            self.btnPkgKeywords.hide()
        
        # Connect option toggles to on_toggled
        for checkbutton in self.wtree.get_widget("table2").get_children():
            if isinstance(checkbutton, gtk.CheckButton):
                checkbutton.connect("toggled", self.on_toggled)
            else:
                dprint("ADVEMERGE: table2 has child not of type gtk.CheckButton")
                dprint(checkbutton)
        
        if not self.prefs.advemerge.showuseflags:
            self.use_flags_frame.hide()
        if not self.prefs.advemerge.showkeywords:
            self.keywords_frame.hide()
        
        # Make tool tips available
        self.tooltips = gtk.Tooltips()
      
        # Build version combo list
        self.get_versions()
        
        # Build a formatted combo list from the versioninfo list 
        self.comboList = gtk.ListStore(str)
        index = 0
        for x in range(len(self.verList)):
            ver = self.verList[x]
            info = ver["number"]
            slot = ver["slot"]
            if slot != '0':
                info += ''.join(['   [', _('Slot:%s') % slot, ']'])
            if not ver["available"]:
                info += _('   {unavailable}')
            elif not ver["stable"]:
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
            
            self.comboList.append([info])
        
        # Build version combobox
        self.combobox = self.wtree.get_widget("cmbVersion")
        self.combobox.set_model(self.comboList)
        cell = gtk.CellRendererText()
        self.combobox.pack_start(cell, True)
        self.combobox.add_attribute(cell, 'text', 0)
        self.combobox.set_active(index) # select "recommended" ebuild by default
        
        # emerge / unmerge combobox:
        self.emerge_combolist = gtk.ListStore(str)
        iter = self.emerge_combolist.append(["emerge"])
        self.emerge_combolist.append(["unmerge"])
        self.emerge_combobox = self.wtree.get_widget("cmbEmerge")
        self.emerge_combobox.set_model(self.emerge_combolist)
        cell = gtk.CellRendererText()
        self.emerge_combobox.pack_start(cell, True)
        self.emerge_combobox.add_attribute(cell, 'text', 0)
        self.emerge_combobox.set_active_iter(iter)
        
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
        if self.prefs.emerge.nospinner:
            self.wtree.get_widget("cbNoSpinner").set_active(True)
        
        # show command in command_label
        self.display_emerge_command()

    #-----------------------------------------------
    # GUI Callback function definitions start here
    #-----------------------------------------------

    def ok_clicked(self, widget):
        """ Interrogate object for settings and start the ebuild """
        command = self.get_command()
        
        # Dispose of the dialog
        self.window.destroy()
        
        # Submit the command for processing
        self.setup_command(self.package.get_name(), command)

    def cancel_clicked(self, widget):
        """ Cancel emerge """
        self.window.destroy()


    def help_clicked(self, widget):
        """ Display help file with web browser """
        load_web_page('file://' + self.prefs.DATA_PATH + 'help/advemerge.html', self.prefs)

    def version_changed(self, widget):
        """ Version has changed, update the dialog window """
        dprint("ADVEMERGE: changing version")
        iter = self.combobox.get_active_iter()
        model = self.combobox.get_model()
        sel_ver = model.get_value(iter, 0)
        if len(sel_ver) > 2:
            verInfo = self.current_verInfo = self.get_verInfo(sel_ver)
            # Reset use flags
            self.build_use_flag_widget(verInfo["use_flags"], verInfo["name"])
            # Reset keywords
            self.build_keywords_widget(verInfo["keywords"])
        self.display_emerge_command()
    
    def emerge_changed(self, widget):
        """ Swap between emerge and unmerge """
        dprint("ADVEMERGE: emerge_changed()")
        iter = self.emerge_combobox.get_active_iter()
        model = self.emerge_combobox.get_model()
        self.emerge_unmerge = model.get_value(iter, 0)
        self.display_emerge_command()
    
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

    def on_toggled(self, widget):
        self.display_emerge_command()
        return False
    
    def on_package_use_commit(self, button_widget):
        dprint("ADVEMERGE: on_package_use_commit()")
        use_flags = self.get_use_flags()
        if not use_flags: return
        addlist = use_flags.split()
        removelist = []
        for item in addlist: # get opposite of flags
            if item.startswith('-'):
                removelist.append(item[1:])
            else:
                removelist.append('-' + item)
        okay = portagelib.set_user_config( self.prefs,\
                'package.use', name=self.package.full_name,
                add=addlist, remove=removelist, callback=self.reload )
    
    def on_make_conf_commit(self, button_widget):
        dprint("ADVEMERGE: on_make_conf_commit()")
        use_flags = self.get_use_flags()
        if not use_flags: return
        addlist = use_flags.split()
        removelist = []
        for item in addlist: # get opposite of flags
            if item.startswith('-'):
                removelist.append(item[1:])
            else:
                removelist.append('-' + item)
        # set_user_config must be performed after set_make_conf has finished or we get problems.
        # we need to set package.use in case the flag was set there originally!
        package_use_callback = Dispatcher( portagelib.set_user_config, self.prefs, \
                'package.use', self.package.full_name, '', '', removelist, self.reload )
        portagelib.set_make_conf( self.prefs, \
            'USE', add=addlist, remove=removelist, callback=package_use_callback )
    
    def on_package_keywords_commit(self, button_widget):
        dprint("ADVEMERGE: on_package_keywords_commit()")
        keyword = self.get_keyword()
        if not keyword: return
        addlist = [keyword]
        if keyword.startswith("-"):
            removelist = [keyword[1:]]
        else:
            removelist = ["-" + keyword]
        verInfo = self.current_verInfo
        ebuild = verInfo["name"]
        okay = portagelib.set_user_config( self.prefs, \
            'package.keywords', ebuild=ebuild, add=addlist, remove=removelist, callback=self.reload)
    
    #------------------------------------------
    # Support function definitions start here
    #------------------------------------------

    def reload(self):
        """ Reload package info """
        # This is the callback for changes to portage config files, so we need to reload portage
        self.re_init_portage()
        
        # Also delete properties for the current ebuild so they are refreshed
        verInfo = self.current_verInfo
        ebuild = verInfo["name"]
        #~ if ebuild in self.package.properties:
            #~ # Remove properties object so everything's recalculated
            #~ del self.package.properties[ebuild]
        # Remove properties object so everything's recalculated
        self.package.properties.pop(ebuild, None)
        self.system_use_flags = portagelib.SystemUseFlags
        self.package_use_flags = portagelib.get_user_config('package.use', self.package.full_name)
        #dprint(self.package_use_flags)
        
        self.current_verInfo = None
        self.get_versions()
        
        oldindex = self.combobox.get_active()
        
        # Rebuild version liststore
        self.comboList = gtk.ListStore(str)
        index = 0
        for x in range(len(self.verList)):
            ver = self.verList[x]
            info = ver["number"]
            slot = ver["slot"]
            if slot != '0':
                info += ''.join(['   [', _('Slot:%s') % slot, ']'])
            if not ver["available"]:
                info += _('   {unavailable}')
            elif not ver["stable"]:
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
            
            self.comboList.append([info])
        
        self.combobox.set_model(self.comboList)
        self.combobox.set_active(oldindex)
        
        self.display_emerge_command()
    
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
            info["available"] = False if the ebuild is no longer available
        """ 
        self.verList = []
        # Get all versions sorted in chronological order
        portage_versions = self.package.get_versions()
 
        # Get all installed versions
        installed = self.package.get_installed()
        
        ebuilds = portage_versions[:]
        for item in installed:
            if item not in portage_versions:
                ebuilds.append(item)
        
        ebuilds = ver_sort(ebuilds)
        
        # get lists of hard masked and stable versions (unstable inferred)
        hardmasked = self.package.get_hard_masked(check_unmask = True)
        nonmasked = self.package.get_versions(include_masked = False)
        
        # iterate through ebuild list and create data structure
        for ebuild in ebuilds:
            info = {}
            props = self.package.get_properties(ebuild) 
            info["name"] = ebuild
            info["number"] = portagelib.get_version(ebuild)
            if ebuild == self.package.get_best_ebuild():
                info["best"] = True
                info["best_downgrades"] = ebuild not in portagelib.best(installed + [ebuild])
            else:
                info["best"] = info["best_downgrades"] = False
            info["installed"] = ebuild in installed
            info["slot"] = props.get_slot()
            info["keywords"] = props.get_keywords()
            info["use_flags"] = props.get_use_flags()
            info["stable"] = ebuild in nonmasked
            info["hard_masked"] = ebuild in hardmasked
            info["available"] = ebuild in portage_versions
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
                verInfo = self.current_verInfo
                if keyword == None: # i.e. "None" is selected
                    # check to see if the ebuild is keyword unmasked,
                    if verInfo["stable"] and self.arch not in verInfo["keywords"]:
                        # i.e. "~arch" is in keywords, not "arch" => must be unmasked
                        # so: re-mask it (for use with package.keywords button)
                        return "-~" + self.arch
                    keyword = ''
                if verInfo["stable"]: return ''
                return keyword.strip()
        return ''

    def get_use_flags(self, ebuild=None):
        """ Get use flags selected by user """
        if not ebuild:
            iter = self.combobox.get_active_iter()
            model = self.combobox.get_model()
            sel_ver = model.get_value(iter, 0)
            verInfo = self.get_verInfo(sel_ver)
            ebuild = verInfo["name"]
        flaglist = []
        if ebuild in self.package_use_flags: #.has_key(ebuild):
            ebuild_use_flags = self.system_use_flags + self.package_use_flags[ebuild]
        else:
            ebuild_use_flags = self.system_use_flags
        for child in self.ufList:
            flag = child[1]
            if flag in ebuild_use_flags and '-' + flag in ebuild_use_flags:
                # check to see which comes last (this will be the applicable one)
                ebuild_use_flags.reverse()
                if ebuild_use_flags.index(flag) < ebuild_use_flags.index('-' + flag):
                    flag_active = True
                else:
                    flag_active = False
                ebuild_use_flags.reverse()
            elif flag in ebuild_use_flags:
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
                ('cbNoSpinner', '--nospinner ', '--nospinner '),
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
        #if self.prefs.emerge.nospinner:
        #    options += '--nospinner '
        return options

    def get_command(self):
        # Get selected version from combo list
        iter = self.combobox.get_active_iter()
        model = self.combobox.get_model()
        sel_ver = model.get_value(iter, 0)
        
        # Get version info of selected version
        verInfo = self.get_verInfo(sel_ver)
        
        # Build use flag string
        use_flags = self.get_use_flags(verInfo["name"])
        if len(use_flags) > 0:
            use_flags = "USE='" + use_flags + "' "
            self.btnPkgUse.set_sensitive(True)
            self.btnMakeConf.set_sensitive(True)
        else:
            self.btnPkgUse.set_sensitive(False)
            self.btnMakeConf.set_sensitive(False)
        
        # Build accept keyword string
        accept_keyword = self.get_keyword()
        if len(accept_keyword) > 0:
            accept_keyword = "ACCEPT_KEYWORDS='" + accept_keyword + "' "
            self.btnPkgKeywords.set_sensitive(True)
        else:
            self.btnPkgKeywords.set_sensitive(False)
        
        # Build emerge or unmerge base command
        if (self.is_root or self.wtree.get_widget("cbPretend").get_active()):
            emerge_unmerge = ''
        else:
            emerge_unmerge = 'sudo -p "Password: " '
        
        if self.emerge_unmerge == "emerge":
            emerge_unmerge += "emerge "
        else: # self.emerge_unmerge == "unmerge"
            emerge_unmerge += "emerge unmerge "
        
        # Send command to be processed
        command = ''.join([ \
            use_flags,
            accept_keyword,
            emerge_unmerge,
            self.get_options(),
            '=',
            verInfo["name"]
        ])
        return command
    
    def display_emerge_command(self):
        command = self.get_command()
        end = self.command_buffer.get_end_iter()
        start = self.command_buffer.get_start_iter()
        self.command_buffer.delete(start, end)
        self.command_buffer.insert(self.command_buffer.get_end_iter(), command)
    
    def build_use_flag_widget(self, use_flags, ebuild):
        """ Create a table layout and populate it with 
            checkbox widgets representing the available
            use flags
        """
        dprint("ADVEMERGE: build_use_flag_widget()")
        UseFlagFrame = self.wtree.get_widget("frameUseFlags")
        button_make_conf = self.wtree.get_widget("button_make_conf")
        button_package_use = self.wtree.get_widget("button_package_use")
        # If frame has any children, remove them
        child = UseFlagFrame.child
        if child != None:
            UseFlagFrame.remove(child)
        # If no use flags, hide the frame
        if not use_flags:
            UseFlagFrame.hide()
            self.btnMakeConf.hide()
            self.btnPkgUse.hide()
        else:
            UseFlagFrame.show()
            if self.is_root or utils.can_gksu():
                self.btnPkgUse.show()
                if self.prefs.advemerge.show_make_conf_button:
                    self.btnMakeConf.show()
                else:
                    self.btnMakeConf.hide()
        # Build table to hold checkboxes
        size = len(use_flags)
        maxcol = 4  # = number of columns - 1 = index of last column
        maxrow = (size - 1) / (maxcol + 1)  # = number of rows - 1
        # resize the table if it's taller than it is wide
        table = gtk.Table(maxrow+1, maxcol+1, True)
        if maxrow + 1 >= 6: # perhaps have this number configurable?
            # perhaps add window based on size (in pixels) of table somehow...
            scrolledwindow = gtk.ScrolledWindow()
            scrolledwindow.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            UseFlagFrame.add(scrolledwindow)
            scrolledwindow.add_with_viewport(table)
            scrolledwindow.set_size_request(1, 100) # min height of 100 pixels
            scrolledwindow.show()
        else:
            UseFlagFrame.add(table)
        
        self.ufList = []
        
        # Iterate through use flags collection, create checkboxes
        # and attach to table
        col = 0
        row = 0
        if ebuild in self.package_use_flags: #.has_key(ebuild):
            ebuild_use_flags = self.system_use_flags + self.package_use_flags[ebuild]
        else:
            ebuild_use_flags = self.system_use_flags
        for flag in use_flags:
            if flag in ebuild_use_flags and '-' + flag in ebuild_use_flags:
                # check to see which comes last (this will be the applicable one)
                ebuild_use_flags.reverse()
                if ebuild_use_flags.index(flag) < ebuild_use_flags.index('-' + flag):
                    flag_active = True
                else:
                    flag_active = False
                ebuild_use_flags.reverse()
            elif flag in ebuild_use_flags:
                flag_active = True
            else:
                flag_active = False
            button = gtk.CheckButton(flag)
            button.set_active(flag_active)
            self.ufList.append([button, flag])

            # Add tooltip, attach button to table and show it off
            # Use lower case flag, since that is how it is stored
            # in the UseFlagDict.  In case flag doesn't exist
            # we'll trap the error

            try:
                self.tooltips.set_tip(button, portagelib.UseFlagDict[flag.lower()][2])
            except KeyError:
                self.tooltips.set_tip(button, _('Unsupported use flag'))
            table.attach(button, col, col+1, row, row+1)
            # connect to on_toggled so we can show changes
            button.connect("toggled", self.on_toggled)
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
        self.kwList.append([button, None])
        rbGroup = button
        table.attach(button, col, col+1, row, row+1)
        button.show()
        col += 1
        button_added = False
        clickable_button = False
        for keyword in keywords:
            if keyword[0] == '~':
                if (keyword[1:] == self.arch) or \
                        (self.prefs.globals.enable_archlist and 
                            (keyword[1:] in self.prefs.globals.archlist)):
                    button = gtk.RadioButton(rbGroup, keyword)
                    self.kwList.append([button, keyword])
                    table.attach(button, col, col+1, row, row+1)
                    # connect to on_toggled so we can show changes
                    button.connect("toggled", self.on_toggled)
                    button.show()
                    button_added = True
                    clickable_button = True
                    if keyword[1:] == self.arch and self.current_verInfo["stable"]:
                        # i.e. package has been keyword unmasked already
                        button.set_active(True)
            else:
                if (keyword == self.arch) or \
                        (self.prefs.globals.enable_archlist and 
                            (keyword in self.prefs.globals.archlist)):
                    label = gtk.Label(keyword)
                    label.set_alignment(.05, .5)
                    table.attach(label, col, col+1, row, row+1)
                    label.show()
                    button_added = True
            # Increment col & row counters
            if button_added:
                col += 1
                if col > maxcol:
                    col = 0
                    row += 1
        if clickable_button:
            # Display the entire table
            table.show()
            KeywordsFrame.show()
            if self.is_root or utils.can_gksu():
                self.btnPkgKeywords.show()
        else:
            KeywordsFrame.hide()
            self.btnPkgKeywords.hide()

