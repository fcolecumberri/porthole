#!/usr/bin/env python

'''
    Porthole Utils Package
    Holds common functions for Porthole

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Daniel G. Taylor
    Brian Dolbec, Wm. F. Wheeler, Tommy Iorns

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
print "PREFERENCES: id initialized to ", id

import os 
from gettext import gettext as _
from types import *

from porthole.version import version
from porthole._xml.xmlmgr import XMLManager, XMLManagerError
from porthole.utils import debug
print "PREFERENCES: imported debug.id = ", debug.id
from porthole.utils.utils import get_user_home_dir, can_gksu
 
class OptionsClass:
    """Blank class to hold options"""
    
    def __repr__(self):
        """Return options as a string"""
        return self.__dict__.__repr__()

class EmergeOptions(OptionsClass):
    """ Holds common emerge options """
    def __init__(self):
        # let's get some saved values in here!
        self.pretend = False
        self.fetch = False
        self.verbose = False
        self.update = False
        self.nospinner = True # currently hidden
        self.noreplace = True
        self.oneshot = False
        # not really used for emerge options
        # we use our own internal seach, just here for convienience
        #self.search_descriptions1 = False

    def get_string(self):
        """ Return currently set options in a string """
        opt_string = ' '
        if self.pretend:   opt_string += '--pretend '
        if self.fetch:     opt_string += '--fetchonly '
        if self.verbose:   opt_string += '--verbose '
        if self.update: opt_string += '--update '
        if self.nospinner: opt_string += '--nospinner '
        if self.noreplace: opt_string += '--noreplace '
        if self.oneshot: opt_string += '--oneshot '
        return opt_string

class PortholePreferences:
    """ Holds all of Porthole's user configurable preferences """
    def __init__(self, New_prefs = None):

        # establish path & name of user prefs file

        home = get_user_home_dir()
        self.__PFILE = home + "/.porthole/prefs.xml"

        # check if directory exists, if not create it
        if not os.access(home + "/.porthole", os.F_OK):
           debug.dprint("PREFERENCES: ~/.porthole does not exist, creating...")
           os.mkdir(home + "/.porthole")

        # open prefs file if we have access to the file  
        # or simply create an empty XML doc

        if os.access(self.__PFILE, os.F_OK):
           debug.dprint("PREFERENCES: loading preferences from file: %s..." % self.__PFILE)
           dom = XMLManager(self.__PFILE)
        else:
           dom = XMLManager(None)
           dom.name = 'portholeprefs'
           dom.version = version

        # Load user preferences from XML file.  If the node doesn't exist,
        # set pref to default value.  The beauty of this is: older versions
        # of the prefs files are still compatible and even if the user has
        # no prefs file, it still works!
        
        preflist = {}
        
        preflist['main'] = [ \
            ['width', 200],
            ['height', 350],
            ['xpos', False],
            ['ypos', False],
            ['hpane', 180],
            ['vpane', 125],
            ['maximized', False],
            ['search_desc', False],
            ['show_nag_dialog', True]
        ]
        
        preflist['process'] = [ \
            ['width', 300],
            ['height', 350],
            ['width_verbose', 500]
        ]
        
        preflist['terminal'] = [ \
            ['width', 300],
            ['height', 350],
            ['width_verbose', 500],
            ['all_tabs_use_custom_colors', False],
            ['font', None]
        ]
        
        history = ["",
                   "emerge ",
                   "ACCEPT_KEYWORDS='~x86' emerge ",
                   "USE=' ' emerge ",
                   "ACCEPT_KEYWORDS='~x86' USE=' ' emerge ",
                   "emerge --help"]
        # default_history = length of the history items to always remain
        # at the start of the popdown history list & set above when history is set
        # history_length = Default value for maximum nuber of retained history items
        
        preflist['run_dialog'] = [ \
            ['width', 400],
            ['height', 120],
            ['history', history],
            ['default_history', len(history)],
            ['history_length', 10]
        ]
        
        for window_name in preflist.keys():
            setattr(self, window_name, OptionsClass()) # construct self.main etc.
            for pref_name, default_value in preflist[window_name]:
                try:
                    value = dom.getitem('/'.join(['/window',window_name,pref_name]))
                    # (e.g. '/window/main/width')
                except XMLManagerError:
                    value = default_value
                setattr(getattr(self, window_name), pref_name, value) # set self.main.width etc
        
        # Formatting tags for the terminal window tabs.  
        # Note: normal font weight = 400 (pango.WEIGHT_NORMAL),
        #       bold = 700 (pango.WEIGHT_BOLD)
        # Note: all colors are in hex for future color editor;
        #       '' means use default color.
        
        self.TAG_DICT = {}
        
        taglist = [ \
            ['default','','',400],
            ['caution','','#c040b0',400],  # [name, default forecolor, backcolor, fontweight]
            ['command','#ffffff','#000080',700],
            ['emerge','','#90ee90',700],
            ['error','#faf0e6','#ff0000',700],
            ['info','','#b0ffff',400],
            ['linenumber','#0000ff','',700],
            ['note','#8b008b','',400],
            ['warning','','#eeee80',400],
            # the following tags are for emerge's output formatting
            ['bold','','',700],
            ['light','','',300],
            ['fg_black','black','',None],
            ['fg_red','darkred','',None],
            ['fg_green','darkgreen','',None],
            ['fg_yellow','brown','',None],
            ['fg_blue','darkblue','',None],
            ['fg_magenta','magenta','',None],
            ['fg_cyan','blue','',None],
            ['fg_white','yellow','',None],
            ['bg_black','','black',None],
            ['bg_red','','darkred',None],
            ['bg_green','','darkgreen',None],
            ['bg_yellow','','brown',None],
            ['bg_blue','','darkblue',None],
            ['bg_magenta','','magenta',None],
            ['bg_cyan','','blue',None],
            ['bg_white','','white',None],
        ]
        
        for tag_name, forecolor, backcolor, fontweight in taglist:
            try:
                fc = dom.getitem(''.join(['/window/terminal/tag/',tag_name,'/forecolor']))
            except XMLManagerError:
                fc = forecolor
            try:
                bc = dom.getitem(''.join(['/window/terminal/tag/',tag_name,'/backcolor']))
            except XMLManagerError:
                bc = backcolor
            try:
                fw = dom.getitem(''.join(['/window/terminal/tag/',tag_name,'/fontweight']))
            except XMLManagerError:
                fw = fontweight
            self.TAG_DICT[tag_name] = [fc, bc, fw]
        
        emergeoptions = ['pretend', 'fetch', 'verbose', 'update', 'nospinner', 'noreplace', 'oneshot'] # 'search_descriptions']
        self.emerge = EmergeOptions()
        for option in emergeoptions:
            try:
                setattr(self.emerge, option, dom.getitem(''.join(['/emerge/options/', option])))
            except XMLManagerError:
                pass # defaults set in EmergeOptions class
        
        advemergeoptions = [
            ['showuseflags', True],
            ['showkeywords', True],
            ['show_make_conf_button', False],
        ]
        self.advemerge = OptionsClass()
        for option, default in advemergeoptions:
            try:
                value = dom.getitem(''.join(['/advemerge/', option]))
            except XMLManagerError:
                value = default
            setattr(self.advemerge, option, value)
        
        viewoptions = [ \
            ['downgradable_fg', '#FA0000'],
            ['upgradable_fg', '#0000FF'],
            ['normal_fg','#000000'],
            ['normal_bg','#FFFFFF']
        ]
        self.views = OptionsClass()
        for option, default in viewoptions:
            try:
                value = dom.getitem(''.join(['/views/', option]))
            except XMLManagerError:
                value = default
            setattr(self.views, option, value)
        
        summaryoptions = [ \
            ['showtable', True],
            ['showkeywords', True],
            ['showinstalled', True],
            ['showavailable', True],
            ['showlongdesc', True],
            ['showuseflags', True],
            ['showlicense', True],
            ['showurl', True],
            ['ebuilds_top', True],
        ]
        self.summary = OptionsClass()
        for option, default in summaryoptions:
            try:
                value = dom.getitem(''.join(['/summary/', option]))
            except XMLManagerError:
                value = default
            setattr(self.summary, option, value)
        
        # Misc. variables
        
        # probably depricated variables, was used for progressbar calc
        try:
           self.database_size = dom.getitem('/database/size')
        except XMLManagerError:
           self.database_size = 7000
        #~ try:
           #~ self.dbtime = dom.getitem('/database/dbtime')
           #~ #debug.dprint("PREFS: __init__(); self.dbtime =")
           #~ #debug.dprint(self.dbtime)
        #~ except XMLManagerError:
           #~ self.dbtime = 50
        #~ try:
           #~ self.dbtotals = dom.getitem('/database/dbtotals')
        #~ except XMLManagerError:
           #~ self.dbtotals = []
        
        self.plugins = OptionsClass()
        
        globaloptions = [ \
            ['LANG', 'en'],
            ['enable_archlist', False],
            ##['enable_all_keywords', False],
            ["archlist", ["alpha", "amd64", "arm", "hppa", "ia64", "mips",
                            "ppc", "ppc64", "s390", "sparc", "x86"]],
            ["Sync", "emerge --sync"],
            ["Sync_label", _("Sync")],
            #                use the form " [sync-command, sync-label],
            # note: this is now hard-coded below
            #["Sync_methods", [['emerge sync', _('Sync')],
            #                  ['emerge-webrsync', _('WebRsync')],
            #                  ['#user defined', _('Unknown Sync')]]],
            ['custom_browser_command', 'firefox %s'],
            ['use_custom_browser', False],
            ['su', 'gksudo -g'] # -g tells gksu not to steal mouse / keyboard focus. Panics sometimes otherwise.
        ]
        
        self.globals = OptionsClass()
        for option, default in globaloptions:
            try:
                value = dom.getitem(''.join(['/globals/', option]))
                if type(value) == StringType: # remove xml indent padding
                   value = value.strip()
                if value == "emerge sync": # upgrade from depricated action 'sync'
                    value = default
            except XMLManagerError:
                value = default
                debug.dprint("PREFERENCES: DEFAULT VALUE: %s = %s" %(option,str(value)))
            setattr(self.globals, option, value)
            debug.dprint("PREFERENCES: PortholePreferences; setting globals.%s = %s" %(option, str(value)))
        # create a keyworded archlist
        self.globals.keyworded_archlist = []
        for arch in self.globals.archlist:
            self.globals.keyworded_archlist.append('~'+arch)
        
        if can_gksu(self.globals.su.split(' ')[0]) == False:
            # If the current su option is not valid, try some others.
            if can_gksu('gksudo'):
                self.globals.su = 'gksudo -g'
            elif can_gksu('gksu'):
                self.globals.su = 'gksu -g'
            elif can_gksu('gnomesu'):
                self.globals.su = 'gnomesu'
            elif can_gksu('kdesu'):
                self.globals.su = 'kdesu'
        
        self.globals.Sync_methods = [['emerge --sync', _('Sync')],
                                     ['emerge-webrsync', _('WebRsync')]]
        
        # fix sync_label if translation changed
        for method in self.globals.Sync_methods:
            if method[0] == self.globals.Sync:
                self.globals.Sync_label = method[1]
        
        if New_prefs:
            for option, value in New_prefs:
                setattr(self, option, value)
        debug.dprint("PREFERENCES: PortholePreferences;  DATA_PATH = " + self.DATA_PATH)
        if self.DATA_PATH == '/usr/share/porthole/': # installed version running
            # find our installed location
            import sys
            self.PACKAGE_DIR = sys.path[0] 
            debug.dprint("PREFERENCES: PortholePreferences;  PACKAGE_DIR = " + self.PACKAGE_DIR)
            # set the correct path to the AUTHORS file
            self.AUTHORS = self.DATA_PATH + "AUTHORS"
        else:
            self.PACKAGE_DIR = self.DATA_PATH
            # running a checkout, set it up one directory. go 2 since the data_path ends in a '/'
            self.AUTHORS = '/'.join((self.DATA_PATH.split('/'))[:-2] + ["AUTHORS"])
        debug.dprint("PREFERENCES: PortholePreferences; AUTHORS = " + self.AUTHORS)
        self.PLUGIN_DIR = self.PACKAGE_DIR + '/plugins/' # could add more dirs later
        debug.dprint("PREFERENCES: PortholePreferences; PLUGIN_DIR = " + self.PLUGIN_DIR)
        self.plugins = OptionsClass()
        try:
            option = "active_list"
            value = dom.getitem(''.join(['/plugins/', option]))
        except XMLManagerError:
            value = []
        setattr(self.plugins, option, value)
        debug.dprint("PREFERENCES: PortholePreferences; setting plugins.%s = %s" %(option, str(value)))

        # All prefs now loaded or defaulted
        del dom   # no longer needed, release memory

    def save(self):
        """ Save preferences """
        debug.dprint("PREFERENCES: preferences save()")
        dom = XMLManager(None)
        dom.name = 'portholeprefs'
        dom.version = version
        dom.additem('/window/main/width', self.main.width)
        dom.additem('/window/main/height', self.main.height)
        dom.additem('/window/main/xpos', self.main.xpos)
        dom.additem('/window/main/ypos', self.main.ypos)
        dom.additem('/window/main/hpane', self.main.hpane)
        #debug.dprint("PREFS: save() hpane: %d" %self.main.hpane)
        dom.additem('/window/main/vpane', self.main.vpane)
        dom.additem('/window/main/maximized', self.main.maximized)
        dom.additem('/window/main/search_desc', self.main.search_desc)
        dom.additem('/window/main/show_nag_dialog', self.main.show_nag_dialog)
        dom.additem('/window/process/width', self.process.width)
        dom.additem('/window/process/height', self.process.height)
        dom.additem('/window/process/width_verbose', self.process.width_verbose)
        dom.additem('/window/terminal/width', self.terminal.width)
        dom.additem('/window/terminal/height', self.terminal.height)
        dom.additem('/window/terminal/width_verbose', self.terminal.width_verbose)
        dom.additem('/window/terminal/font', self.terminal.font)
        dom.additem('/window/terminal/all_tabs_use_custom_colors', \
            self.terminal.all_tabs_use_custom_colors)
        # generate tag keys from dictionary
        for key in self.TAG_DICT:
            format_list = self.TAG_DICT[key] 
            dom.additem('/window/terminal/tag/' + key + '/forecolor', format_list[0])
            dom.additem('/window/terminal/tag/' + key + '/backcolor', format_list[1])
            dom.additem('/window/terminal/tag/' + key + '/fontweight', format_list[2])
        dom.additem('/window/run_dialog/width', self.run_dialog.width)
        dom.additem('/window/run_dialog/height', self.run_dialog.height)
        dom.additem('/window/run_dialog/history', self.run_dialog.history)
        dom.additem('/window/run_dialog/default_history', self.run_dialog.default_history)
        dom.additem('/window/run_dialog/history_length', self.run_dialog.history_length)
        dom.additem('/emerge/options/pretend', self.emerge.pretend)
        dom.additem('/emerge/options/fetch', self.emerge.fetch)
        dom.additem('/emerge/options/verbose', self.emerge.verbose)
        dom.additem('/emerge/options/update', self.emerge.update)
        dom.additem('/emerge/options/nospinner', self.emerge.nospinner)
        dom.additem('/emerge/options/noreplace', self.emerge.noreplace)
        dom.additem('/emerge/options/oneshot', self.emerge.oneshot)
        #dom.additem('/emerge/options/search_descriptions1', self.emerge.search_descriptions1)
        dom.additem('/advemerge/showuseflags', self.advemerge.showuseflags)
        dom.additem('/advemerge/showkeywords', self.advemerge.showkeywords)
        dom.additem('/advemerge/show_make_conf_button', self.advemerge.show_make_conf_button)
        dom.additem('/views/upgradable_fg', self.views.upgradable_fg)
        dom.additem('/views/downgradable_fg', self.views.downgradable_fg)
        dom.additem('/views/normal_fg', self.views.normal_fg)
        dom.additem('/views/normal_bg', self.views.normal_bg)
        dom.additem('/summary/showtable', self.summary.showtable)
        dom.additem('/summary/showkeywords', self.summary.showkeywords)
        dom.additem('/summary/showinstalled', self.summary.showinstalled)
        dom.additem('/summary/showavailable', self.summary.showavailable)
        dom.additem('/summary/showlongdesc', self.summary.showlongdesc)
        dom.additem('/summary/showuseflags', self.summary.showuseflags)
        dom.additem('/summary/showlicense', self.summary.showlicense)
        dom.additem('/summary/showurl', self.summary.showurl)
        dom.additem('/database/size', self.database_size)
        #debug.dprint("PREFS: save(); self.dbtime = %d" %self.dbtime)
        #dom.additem('/database/dbtime', self.dbtime)
        #dom.additem('/database/dbtotals', self.dbtotals)
        #dom.additem('/plugins/path_list', self.plugins.path_list)
        dom.additem('/globals/LANG', self.globals.LANG)
        dom.additem('/globals/enable_archlist', self.globals.enable_archlist)
        ##dom.additem('/globals/enable_all_keywords', self.globals.enable_all_keywords)
        dom.additem('/globals/archlist', self.globals.archlist)
        dom.additem('/globals/Sync', self.globals.Sync)
        dom.additem('/globals/Sync_label', self.globals.Sync_label)
        #dom.additem('/globals/Sync_methods', self.globals.Sync_methods)
        dom.additem('/globals/custom_browser_command', self.globals.custom_browser_command)
        dom.additem('/globals/use_custom_browser', self.globals.use_custom_browser)
        dom.additem('/globals/su', self.globals.su)
        dom.additem('/plugins/active_list', self.plugins.active_list)
        dom.save(self.__PFILE)
        del dom   # no longer needed, release memory
    
    def __repr__(self): # used by print statement (and pycrash)
        """Return a string representation of the preferences"""
        return self.__dict__.__repr__()

    def add(self, New_prefs = None):
        if New_prefs:
            for option, value in New_prefs:
                setattr(self, option, value)
