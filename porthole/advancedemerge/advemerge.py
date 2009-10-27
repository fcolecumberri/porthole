#!/usr/bin/env python

'''
    Porthole Advanced Emerge Dialog
    Allows the user to set options, use flags, keywords and select
    specific versions.  Has lots of tool tips, too.

    Copyright (C) 2003 - 2009 Fredrik Arnerup, Daniel G. Taylor, Brian Dolbec, 
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

import datetime
id = datetime.datetime.now().microsecond
print "ADVEMERGE: id initialized to ", id

import gtk
import gtk.glade
from gettext import gettext as _


from porthole.utils import utils
from porthole.utils import debug
from porthole import config
from porthole import backends
portage_lib = backends.portage_lib
from porthole import db
from porthole.backends.version_sort import ver_sort
from porthole.backends.utilities import get_reduced_flags, abs_list, abs_flag
from porthole.loaders.loaders import load_web_page
from porthole.utils.dispatcher import Dispatcher

class AdvancedEmergeDialog:
    """Class to perform advanced emerge dialog functionality."""

    def __init__(self, package, setup_command, re_init_portage):
        """ Initialize Advanced Emerge Dialog window """
        # Preserve passed parameters
        self.package = package
        self.setup_command = setup_command
        self.re_init_portage = re_init_portage
        self.arch = portage_lib.get_arch()
        self.system_use_flags = portage_lib.settings.SystemUseFlags
        self.emerge_unmerge = "emerge"
        self.is_root = utils.is_root()
        self.package_use_flags = db.userconfigs.get_user_config('USE', package.full_name)
        self.current_verInfo = None
        
        # Parse glade file
        self.gladefile = config.Prefs.DATA_PATH + "glade/advemerge.glade"
        self.wtree = gtk.glade.XML(self.gladefile, "adv_emerge_dialog", config.Prefs.APP)
     
        # register callbacks
        callbacks = {"on_ok_clicked" : self.ok_clicked,
                     "on_help_clicked" : self.help_clicked,
                     "on_cancel_clicked" : self.cancel_clicked,
                     #"on_cbAsk_clicked": self.Ask_clicked,
                     "on_cbOnlyDeps_clicked" : (self.set_one_of, 'cbOnlyDeps', 'cbNoDeps'),
                     "on_cbNoDeps_clicked" : (self.set_one_of, 'cbNoDeps', 'cbOnlyDeps'),
                     "on_cbQuiet_clicked" : (self.set_one_of, 'cbQuiet', 'cbVerbose'),
                     "on_cbVerbose_clicked" : (self.set_one_of, 'cbVerbose', 'cbQuiet'),
                     "on_cbBuildPkg_clicked" : (self.set_one_of, 'cbBuildPkg', 'cbBuildPkgOnly'),
                     "on_cbBuildPkgOnly_clicked" : (self.set_one_of, 'cbBuildPkgOnly', 'cbBuildPkg'),
                     "on_cbUsePkg_clicked" : (self.set_one_of, 'cbUsePkg', 'cbUsePkgOnly'),
                     "on_cbUsePkgOnly_clicked" : (self.set_one_of, 'cbUsePkgOnly', 'cbUsePkg'),
                     "on_cmbVersion_changed" : self.version_changed,
                     "on_cmbEmerge_changed" : self.emerge_changed,
                     "on_btnPkgUse_clicked" : self.on_package_use_commit,
                     "on_btnMakeConf_clicked" : self.on_make_conf_commit,
                     "on_btnPkgKeywords_clicked" : self.on_package_keywords_commit,
                     "on_cbColorY_clicked": (self.set_one_of, 'cbColorY', 'cbColorN'),
                     "on_cbColorN_clicked": (self.set_one_of, 'cbColorN', 'cbColorY'),
                     "on_cbColumns_clicked": (self.set_all, 'cbColumns','cbPretend'),
                     'on_cbWithBDepsY_clicked': (self.set_one_of, 'cbWithBDepsY', 'cbWithBDepsN'),
                     'on_cbWithBDepsN_clicked': (self.set_one_of, 'cbWithBDepsN', 'cbWithBDepsY'),
                     'on_cbGetBinPkg_clicked': (self.set_one_of, 'cbGetBinPkg', 'cbGetBinPkgOnly'),
                     'on_cbGetBinPkgOnly_clicked': (self.set_one_of, 'cbGetBinPkgOnly', 'cbGetBinPkg' ),
                     "on_toggled": self.on_toggled
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
        if not self.is_root and not utils.can_gksu():
            debug.dprint("ADVEMERGE: self.is_root = $s, utils.can_gksu = %s" %(self.is_root, utils.can_gksu))
            self.btnMakeConf.hide()
            self.btnPkgUse.hide()
            self.btnPkgKeywords.hide()
        
        # Connect option toggles to on_toggled
        for checkbutton in self.wtree.get_widget("table2").get_children():
            if isinstance(checkbutton, gtk.CheckButton):
                checkbutton.connect("toggled", self.on_toggled)
            #else:
            #    debug.dprint("ADVEMERGE: table2 has child not of type gtk.CheckButton")
            #    debug.dprint(checkbutton)
        
        if not config.Prefs.advemerge.showuseflags:
            self.use_flags_frame.hide()
        if not config.Prefs.advemerge.showkeywords:
            self.keywords_frame.hide()
        
        # Make tool tips available
        #self.tooltips = gtk.Tooltips()
      
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
        if config.Prefs.emerge.pretend:
            self.wtree.get_widget("cbPretend").set_active(True)
        if config.Prefs.emerge.verbose:
            self.wtree.get_widget("cbVerbose").set_active(True)
        ## this now just references --update, which is probably not the desired behaviour.
        ## perhaps the current version should be indicated somewhere in the dialog
        #if config.Prefs.emerge.upgradeonly:
        #    self.wtree.get_widget("cbUpgradeOnly").set_active(True)
        if config.Prefs.emerge.fetch:
            self.wtree.get_widget("cbFetchOnly").set_active(True)
        if config.Prefs.emerge.nospinner:
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
        load_web_page('file://' + config.Prefs.DATA_PATH + 'help/advemerge.html', config.Prefs)

    def version_changed(self, widget):
        """ Version has changed, update the dialog window """
        debug.dprint("ADVEMERGE: changing version")
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
        debug.dprint("ADVEMERGE: emerge_changed()")
        iter = self.emerge_combobox.get_active_iter()
        model = self.emerge_combobox.get_model()
        self.emerge_unmerge = model.get_value(iter, 0)
        self.display_emerge_command()

    def set_all(self, widget, *args):
        if widget.get_active():
            for x in args:
                self.wtree.get_widget(x).set_active(True)
            return False

    def set_one_of(self, widget, *args):
        if widget.get_active():
            self.wtree.get_widget(args[0]).set_active(True)
            for x in args[1:]:
                self.wtree.get_widget(x).set_active(False)
            return False

    def on_toggled(self, widget):
        self.display_emerge_command()
        return False
    
    def on_package_use_commit(self, button_widget):
        debug.dprint("ADVEMERGE: on_package_use_commit()")
        use_flags = self.get_use_flags()
        if not use_flags: return
        addlist = use_flags.split()
        removelist = []
        for item in addlist: # get opposite of flags
            if item.startswith('-'):
                removelist.append(item[1:])
            else:
                removelist.append('-' + item)
        okay = db.userconfigs.set_user_config('USE', name=self.package.full_name, add=addlist,
                                                                remove=removelist, callback=self.reload, parent_window = self.window )
        self.version_changed(button_widget)
    
    def on_make_conf_commit(self, button_widget):
        debug.dprint("ADVEMERGE: on_make_conf_commit()")
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
        package_use_callback = Dispatcher( db.userconfigs.set_user_config,\
                'USE', self.package.full_name, '', '', removelist, self.reload )
        portage_lib.set_make_conf('USE', add=addlist, remove=removelist, callback=package_use_callback )
        self.version_changed(button_widget)
    
    def on_package_keywords_commit(self, button_widget):
        debug.dprint("ADVEMERGE: on_package_keywords_commit()")
        keyword = self.get_keyword()
        if not keyword: return
        addlist = [keyword]
        if keyword.startswith("-"):
            removelist = [keyword[1:]]
        else:
            removelist = ["-" + keyword]
        verInfo = self.current_verInfo
        ebuild = verInfo["name"]
        okay = db.userconfigs.set_user_config('package.keywords', ebuild=ebuild, add=addlist, remove=removelist, callback=self.reload)
    
    #------------------------------------------
    # Support function definitions start here
    #------------------------------------------

    def reload(self):
        """ Reload package info """
        # This is the callback for changes to portage config files, so we need to reload portage
        ## now done elsewhere
        ##self.re_init_portage()
        
        # Also delete properties for the current ebuild so they are refreshed
        verInfo = self.current_verInfo
        ebuild = verInfo["name"]
        #~ if ebuild in self.package.properties:
            #~ # Remove properties object so everything's recalculated
            #~ del self.package.properties[ebuild]
        # Remove properties object so everything's recalculated
        self.package.properties.pop(ebuild, None)
        self.system_use_flags = portage_lib.settings.SystemUseFlags
        self.package_use_flags = db.userconfigs.get_user_config('USE', self.package.full_name)
        #debug.dprint(self.package_use_flags)
        
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
            info["number"] = portage_lib.get_version(ebuild)
            if ebuild == self.package.get_best_ebuild():
                info["best"] = True
                info["best_downgrades"] = ebuild not in portage_lib.best(installed + [ebuild])
            else:
                info["best"] = info["best_downgrades"] = False
            info["installed"] = ebuild in installed
            info["slot"] = props.get_slot()
            info["keywords"] = props.get_keywords()
            info["use_flags"] = abs_list(props.get_use_flags())
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
            debug.dprint("ADVEMERGE: get_verInfo(); freaking out! what's \"verInfo\"?")
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
                if verInfo["stable"] and keyword in portage_lib.settings.settings["ACCEPT_KEYWORDS"]: return ''
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
        debug.dprint("ADVEMERGE: get_use_flags(); flags = %s" %str(flags))
        return flags

    def get_options(self):
        """ Create keyword list from option checkboxes """
        List = [('cbAlphabetical', '--alphabetical ', '--alphabetical '),
                ('cbAsk', '-a ', '--ask '),
                ('cbBuildPkg', '-b ', '--buildpkg '),
                ('cbBuildPkgOnly', '-B ', '--buildpkgonly '),
                ('cbColorY', '--color y ', '--color y ' ),
                ('cbColorN', '--color n ', '--color n ' ),
                ('cbDebug', '-d ', '--debug '),
                ('cbDeep', '-D ', '--deep '),
                ('cbEmptyTree', '-e ', '--emptytree '),
                ('cbFetchOnly', '-f ', '--fetchonly '),
                ('cbFetchAllUri', '-F ', '--fetch-all-uri '),
                ('cbGetBinPkg', '-g ', '--getbinpkg '),
                ('cbGetBinPkgOnly', '-G ', '--getbinpkgonly '),
                ('cbIgnoreDefaultOptions',  '--ignore-default-opts ', '--ignore-default-opts '),
                ('cbNewUse', '-N ', '--newuse '),
                ('cbNoConfMem', '--noconfmem ', '--noconfmem '),
                ('cbNoDeps', '-O ', '--nodeps '),
                ('cbNoReplace', '-n ', '--noreplace '),
                ('cbNoSpinner', '--nospinner ', '--nospinner '),
                ('cbOneShot', '--oneshot ', '--oneshot '),
                ('cbOnlyDeps', '-o ', '--onlydeps '),
                ('cbPretend','-p ', '--pretend '),
                ('cbColumns', '--columns ', '--columns '),
                ('cbQuiet', '-q ', '--quiet '),
                ('cbTree', '-t ', '--tree '),
                ('cbUpdate','-u ', '--update '),
                ('cbUsePkg', '-k ', '--usepkg '),
                ('cbUsePkgOnly', '-K ', '--usepkgonly '),
                ('cbVerbose', '-v ', '--verbose '),
                ('cbWithBDepsY', '--with-bdeps y ', '--with-bdeps y '),
                ('cbWithBDepsN', '--with-bdeps n ', '--with-bdeps n ')
                ]
        options = ''
        for Name, ShortOption, LongOption in List:
            if self.wtree.get_widget(Name) and self.wtree.get_widget(Name).get_active():
                options += LongOption
        #if config.Prefs.emerge.nospinner:
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
            use_flags = 'USE="' + use_flags + '" '
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
            emerge_unmerge += "emerge --unmerge "
        
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
        debug.dprint("ADVEMERGE: build_use_flag_widget()")
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
                if config.Prefs.advemerge.show_make_conf_button:
                    self.btnMakeConf.show()
                else:
                    self.btnMakeConf.hide()
        # Build table to hold checkboxes
        size = len(use_flags)
        maxcol = 3  # = number of columns - 1 = index of last column
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
        ebuild_use_flags = get_reduced_flags(ebuild)
        for flag in use_flags:
            flag_active = False
            myflag = abs_flag(flag)
            if myflag in ebuild_use_flags:
                flag_active = True
            button = gtk.CheckButton(flag)
            button.set_use_underline(False)
            button.set_active(flag_active)
            self.ufList.append([button, flag])

            # Add tooltip, attach button to table and show it off
            # Use lower case flag, since that is how it is stored
            # in the UseFlagDict.  In case flag doesn't exist
            # we'll trap the error
            button.set_has_tooltip(True)
            try:
                button.set_tooltip_text(portage_lib.settings.UseFlagDict[flag.lower()][2])
            except KeyError:
                button.set_tooltip_text(_('Unsupported use flag'))
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
            if keyword[0] == '~' and (keyword[1:] == self.arch) or \
                        (config.Prefs.globals.enable_archlist and 
                            ((keyword[1:] in config.Prefs.globals.archlist) or  (keyword in config.Prefs.globals.archlist))):
                button = gtk.RadioButton(rbGroup, keyword, use_underline=False)
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
                #if (keyword == self.arch)
                label = gtk.Label(keyword)
                label.set_alignment(.05, .5)
                label.set_use_underline(False)
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

