#!/usr/bin/env python

'''
    Porthole Utils Package
    Holds common functions for Porthole

    Copyright (C) 2003 - 2004 Fredrik Arnerup and Daniel G. Taylor
                              Brian Dolbec and Wm. F. Wheeler

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

# initially set debug to false
debug = False

import os, threading
import errno
import string
import sre
import datetime

#import portagelib

from sys import stderr
from version import *
from xmlmgr import XMLManager, XMLManagerError
from gettext import gettext as _

import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk
import os
import grp
import pwd, cPickle

def dprint(message):
    """Print debug message if debug is true."""
    if debug:
        print >>stderr, message

def dsave(name, item = None):
    """saves 'item' to file 'name' if debug is true"""
    if debug:
        dprint("UTILS: dsave() Pickling 'item' to file: %s" %name)
        # get home directory
        home = pwd.getpwuid(os.getuid())[5]
        # pickle it baby, yeah!
        cPickle.dump(item, open(home + "/.porthole/" + name, "w"))

def get_icon_for_package(package):
    """Return an icon for a package"""
    # if it's installed, find out if it can be upgraded
    if package and package.get_installed():
        icon = gtk.STOCK_YES
    else:
        # just put the STOCK_NO icon
        # switched to blank icon if not installed
        icon = '' # gtk.STOCK_NO
    return icon       

def get_icon_for_upgrade_package(package, prefs):
    """Return an icon and foreground text color for a package"""
    if not package:
        return '', 'blue'
    #  find out if it can be upgraded
    if package.is_upgradable() == 1:  # 1 for only upgrades (no downgrades)
        icon = gtk.STOCK_GO_UP
        color = prefs.upgradable_fg
    else: # it's a downgrade
        icon = gtk.STOCK_GO_DOWN
        color = prefs.downgradable_fg
    return icon, color      

def is_root():
    """Returns true if process runs as root."""
    return os.geteuid() == 0
    
write_access = is_root

def read_access():
    """Return true if user is root or a member of the portage group."""
    # Note: you don't have to be a member of portage to read the database,
    # but portage caching will not work
    portage = 250  # is portage guaranteed to be 250?
    # answer: portage.portage_gid
    try: portage = grp.getgrnam("portage")[2]
    except: pass
    return write_access() or (portage in (os.getgroups() + [os.getegid()]))

sudo_x_ok = os.access('/usr/bin/sudo', os.X_OK)

def can_sudo():
    """ return True if /usr/bin/sudo exists and is executable """
    return sudo_x_ok
    #return False # for testing

def get_treeview_selection( treeview, num = None):
        """Get the value of whatever is selected in a treeview,
        num is the column, if num is nothing, the iter is returned"""
        model, iter = treeview.get_selection().get_selected()
        selection = iter
        if iter:
            if num:
                selection = model.get_value(iter, num)
        return selection

def get_user_home_dir():
    """Return the path to the current user's home dir"""
    return pwd.getpwuid(os.getuid())[5]

def environment():
    """sets up the environment to run sub processes"""
    env = os.environ
    #dprint("UTILS: environment(), env before & after our additions")
    #dprint(env)
    if "FEATURES" in env:
        env["FEATURES"] += ", notitles"
    else:
        env ["FEATURES"] = "notitles"
    #env["NOCOLOR"] = "true"
    #dprint(env)
    return env

class CommonDialog(gtk.Dialog):
    """ A common gtk Dialog class """
    def __init__(self, title, parent, message, callback, button):
        gtk.Dialog.__init__(self, title, parent, gtk.DIALOG_MODAL or
                            gtk.DIALOG_DESTROY_WITH_PARENT, (button, 0))
        # add message
        text = gtk.Label(message)
        text.set_padding(5, 5)
        text.show()
        self.vbox.pack_start(text)
        # register callback
        if not callback:
            callback = self.__callback
        self.connect("response", callback)
        self.show_all()
    
    def __callback(self, widget, response):
        # If no callback is given, just remove the dialog when clicked
        self.destroy()

class YesNoDialog(CommonDialog):
    """ A simple yes/no dialog class """
    def __init__(self, title, parent = None,
                 message = None, callback = None):
        CommonDialog.__init__(self, title, parent, message,
                                           callback, _("_Yes"))
        # add "No" button
        self.add_button(_("_No"), 1)
        

class SingleButtonDialog(CommonDialog):
    """ A simple please wait dialog class """
    def __init__(self, title, parent = None, message = None,
                 callback = None, button = None, progressbar = False):
        CommonDialog.__init__(self, title, parent, message,
                                           callback, button)
        if progressbar:
            self.progbar = gtk.ProgressBar()
            self.progbar.set_text(_("Loading"))
            self.progbar.show()
            self.vbox.add(self.progbar)

class EmergeOptions:
    """ Holds common emerge options """
    def __init__(self):
        # let's get some saved values in here!
        self.pretend = False
        self.fetch = False
        self.verbose = False
        self.upgradeonly = False
        self.nospinner = True # currently hidden

    def get_string(self):
        """ Return currently set options in a string """
        opt_string = ' '
        if self.pretend:   opt_string += '--pretend '
        if self.fetch:     opt_string += '--fetchonly '
        if self.verbose:   opt_string += '--verbose '
        # upgradeonly does not have the desired effect when passed to emerge.
        #if self.upgradeonly: opt_string += '--upgradeonly '
        if self.nospinner: opt_string += '--nospinner '
        return opt_string

##class AdvEmergeOptions:
##    """ Holds common advanced emerge options """
##    def __init__(self):
##        # let's get some saved values in here!
##        self.enable_all_keywords = False
##
##class PluginOptions:
##    """ Holds preferences for plugins """
##    def __init__(self):
##        self.path_list = [os.getcwd()]
##
##class WindowPreferences:
##    """ Holds preferences for a window """
##    def __init__(self, width = 0, height = 0):
##        self.width = width      # width
##        self.height = height    # height
##
##class ViewOptions:
##    """ Holds foreground colors for a package name"""
##    def __init__(self):
##        self.upgradable_fg = ''
##        self.downgradable_fg = ''
##
##class GlobalPreferences:
##    """Holds some global variables"""
##    def __init__(self):
##        self.LANG = None

class OptionsClass:
    """Blank class to hold options"""
    pass

class PortholePreferences:
    """ Holds all of Porthole's user configurable preferences """
    def __init__(self):

        # establish path & name of user prefs file

        home = get_user_home_dir()
        self.__PFILE = home + "/.porthole/prefs.xml"

        # check if directory exists, if not create it
        if not os.access(home + "/.porthole", os.F_OK):
           dprint("PREFS: ~/.porthole does not exist, creating...")
           os.mkdir(home + "/.porthole")

        # open prefs file if we have access to the file  
        # or simply create an empty XML doc

        if os.access(self.__PFILE, os.F_OK):
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
            #setattr(self, window_name, WindowPreferences()) # create self.main etc
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
            ['caution','','#ff14b4',400],  # [name, default forecolor, backcolor, fontweight]
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
        
        emergeoptions = ['pretend', 'fetch', 'verbose', 'upgradeonly', 'nospinner']
        self.emerge = EmergeOptions()
        for option in emergeoptions:
            try:
                setattr(self.emerge, option, dom.getitem(''.join(['/emerge/options/', option])))
            except XMLManagerError:
                pass # defaults set in EmergeOptions class
        
        advemergeoptions = [
            ['showuseflags', True],
            ['showkeywords', True],
            ['showconfigbuttons', False],
            #['archlist', []],
        ]
        #self.advemerge = AdvEmergeOptions()
        self.advemerge = OptionsClass()
        for option, default in advemergeoptions:
            try:
                value = dom.getitem(''.join(['/advemerge/options/', option]))
            except XMLManagerError:
                value = default
            setattr(self.advemerge, option, value)
        
        viewoptions = [ \
            ['downgradable_fg', '#FA0000'],
            ['upgradable_fg', '#000000'], # green?
            ['normal_fg','#000000'],
            ['normal_bg','#FFFFFF']
        ]
        #self.views = ViewOptions()
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
        try:
           self.dbtime = dom.getitem('/database/dbtime')
           #dprint("UTILS: __init__(); self.dbtime =")
           #dprint(self.dbtime)
        except XMLManagerError:
           self.dbtime = 50
        try:
           self.dbtotals = dom.getitem('/database/dbtotals')
        except XMLManagerError:
           self.dbtotals = []
        
        self.plugins = OptionsClass()
        
        globaloptions = [
                        ["LANG", 'en'],
                        ["enable_archlist", True],
                        ['enable_all_keywords', False],
                        ["archlist", ["alpha", "amd64", "arm", "hppa", "ia64", "mips",
                                        "ppc", "ppc64", "s390", "sparc", "x86"]],
                        ["Sync", "emerge sync"],
                        ["Sync_label", _("Sync")],
                        #                use the form " [sync-command, sync-label],
                        ["Sync_methods", [['emerge sync', _('Sync')], ['emerge-webrsync', _('WebRsync')],
                                            ['#user defined', _('Unknown Sync')]]],
        ]
        
        self.globals = OptionsClass()
        for option, default in globaloptions:
            try:
                value = dom.getitem(''.join(['/globals/', option]))
            except XMLManagerError:
                value = default
            setattr(self.globals, option, value)
            dprint("UTILS: PortholePreferences; setting globals.%s = %s" %(option, str(value)))

        # All prefs now loaded or defaulted
        del dom   # no longer needed, release memory

    def init_plugins(self):
        self.PLUGIN_DIRS = [self.DATA_PATH + 'plugins'] # could add more dirs later
        self.plugins.path_list = []
        # search for sub-dirs
        for dir in self.PLUGIN_DIRS:
            list = os.listdir(dir)
            for entry in list:
                if entry != 'CVS': # skip the CVS directory.
                    entry = '/'.join([dir, entry]) # get full path
                    if os.path.isdir(entry):
                        self.plugins.path_list.append(entry)

    def save(self):
        """ Save preferences """
        dprint("UTILS: preferences save()")
        dom = XMLManager(None)
        dom.name = 'portholeprefs'
        dom.version = version
        dom.additem('/window/main/width', self.main.width)
        dom.additem('/window/main/height', self.main.height)
        dom.additem('/window/main/xpos', self.main.xpos)
        dom.additem('/window/main/ypos', self.main.ypos)
        dom.additem('/window/main/hpane', self.main.hpane)
        #dprint("UTILS: save() hpane: %d" %self.main.hpane)
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
        dom.additem('/emerge/options/upgradeonly', self.emerge.upgradeonly)
        dom.additem('/emerge/options/nospinner', self.emerge.nospinner)
        dom.additem('/advemerge/showuseflags', self.advemerge.showuseflags)
        dom.additem('/advemerge/showkeywords', self.advemerge.showkeywords)
        dom.additem('/advemerge/showconfigbuttons', self.advemerge.showconfigbuttons)
        dom.additem('/views/upgradable_fg', self.views.upgradable_fg)
        dom.additem('/views/downgradable_fg', self.views.downgradable_fg)
        dom.additem('/summary/showtable', self.summary.showtable)
        dom.additem('/summary/showkeywords', self.summary.showkeywords)
        dom.additem('/summary/showinstalled', self.summary.showinstalled)
        dom.additem('/summary/showavailable', self.summary.showavailable)
        dom.additem('/summary/showlongdesc', self.summary.showlongdesc)
        dom.additem('/summary/showuseflags', self.summary.showuseflags)
        dom.additem('/summary/showlicense', self.summary.showlicense)
        dom.additem('/summary/showurl', self.summary.showurl)
        dom.additem('/database/size', self.database_size)
        #dprint("UTILS: save(); self.dbtime = %d" %self.dbtime)
        dom.additem('/database/dbtime', self.dbtime)
        dom.additem('/database/dbtotals', self.dbtotals)
        dom.additem('/plugins/path_list', self.plugins.path_list)
        dom.additem('/globals/LANG', self.globals.LANG)
        dom.additem('/globals/enable_archlist', self.globals.enable_archlist)
        dom.additem('/globals/enable_all_keywords', self.globals.enable_all_keywords)
        dom.additem('/globals/archlist', self.globals.archlist)
        dom.additem('/globals/Sync', self.globals.Sync)
        dom.additem('/globals/Sync_label', self.globals.Sync_label)
        dom.additem('/globals/Sync_methods', self.globals.Sync_methods)
        dom.save(self.__PFILE)
        del dom   # no longer needed, release memory


class PortholeConfiguration:
    """ Holds all of Porthole's developer configurable settings """
    def __init__(self, DATA_PATH):
        dom = XMLManager(DATA_PATH + 'configuration.xml')

        # Handle all the regular expressions.  They will be compiled
        # within this object for the sake of efficiency.
        
        filterlist = ['info', 'warning', 'error', 'caution', 'needaction']
        for filter in filterlist:
            patternlist = dom.getitem(''.join(['/re_filters/',filter])) # e.g. '/re_filters/info'
            attrname = ''.join([filter, '_re_list'])
            setattr(self, attrname, []) # e.g. self.info_re_list = []
            for regexp in patternlist:
                getattr(self, attrname).append(sre.compile(regexp))
            patternlist = dom.getitem(''.join(['/re_filters/not',filter])) # e.g. '/re_filters/notinfo'
            attrname = ''.join([filter, '_re_notlist'])
            setattr(self, attrname, []) # e.g. self.info_re_notlist = []
            for regexp in patternlist:
                getattr(self, attrname).append(sre.compile(regexp))
        
        self.emerge_re = sre.compile(dom.getitem('/re_filters/emerge'))
        self.ebuild_re = sre.compile(dom.getitem('/re_filters/ebuild'))
        self.merged_re = sre.compile(dom.getitem('/re_filters/merged'))
        del dom

    def isInfo(self, teststring):
        ''' Parse string, return true if it matches info
            reg exp and its not in the reg exp notlist'''
        for regexp in self.info_re_list:
            if regexp.match(teststring):
                for regexpi in self.info_re_notlist:
                    if regexpi.match(teststring):
                        return False    # excluded, no match
                return True
        return False

    def isWarning(self, teststring):
        ''' Parse string, return true if it matches warning reg exp '''
        for regexp in self.warning_re_list:
            if regexp.match(teststring):
                for regexpi in self.warning_re_notlist:
                    if regexpi.match(teststring):
                        return False    # excluded, no match
                return True
        return False

    def isCaution(self, teststring):
        ''' Parse string, return true if matches caution regexp '''
        for regexp in self.caution_re_list:
            if regexp.match(teststring):
                for regexpi in self.caution_re_notlist:
                    if regexpi.match(teststring):
                        return False    # excluded, no match
                return True
        return False

    def isError(self, teststring):
        ''' Parse string, return true if belongs in error tab '''
        for regexp in self.error_re_list:
            if regexp.match(teststring):
                for regexpi in self.error_re_notlist:
                    if regexpi.match(teststring):
                        return False    # excluded, no match
                return True
        return False

    def isEmerge(self, teststring):
        ''' Parse string, return true if it is the initial emerge line '''
        return self.emerge_re.match(teststring) != None

    def isMerged(self, teststring):
        ''' Parse string, return true if it is the merged line '''
        return self.merged_re.search(teststring) != None
    def isAction(self, teststring):
        '''
        Returns True if teststring matches the pre-set criteria for notification of an
        action the user is recommended to take, such as etc-update or revdep-rebuild.
        '''
        for regexp in self.needaction_re_list:
            if regexp.match(teststring):
                for regexpi in self.needaction_re_notlist:
                    if regexpi.match(teststring):
                        return False    # excluded, no match
                return True
        return False

class BadLogFile(Exception):
    """ Raised when we encounter errors parsing the log file."""

def estimate(package_name, log_file_name="/var/log/emerge.log"):
    """ Estimates, based on previous emerge operations, how long it would
        take to compile a particular package on the system. 
        
        This function returns a 4-tuple with floating point values representing
        the average duration of the compilation of a package.

        When unable to determine an average, the function returns None. """
    try:
        start_time = 0.0
        end_time = 0.0
        total_time = datetime.timedelta()
        emerge_count = 0
        log_file = open(log_file_name)       
        package_name_escaped = ""      
        # Let's excape characters like + before we try to compile the regular
        #expression
        for i in range(0, len(package_name)):
            if package_name[i] == "+" or package_name[i] == "-":
                package_name_escaped += "\\"
            package_name_escaped += package_name[i]
        # Now that we already escaped the "special characters", we
        # can start searching the logs
        start_pattern = sre.compile("^[0-9]+:  >>> emerge.*%s*." %
                                                           package_name_escaped)
        end_pattern = sre.compile("^[0-9]+:  ::: completed emerge.*%s*." %
                                                           package_name_escaped)      
        lines = log_file.readlines()
        for i in range(1, len(lines)):
            if start_pattern.match(lines[i]):
                tokens = lines[i].split()
                start_time = string.atof((tokens[0])[0:-1])               
                for j in range(i+1, len(lines)):
                    if start_pattern.match(lines[j]):
                        # We found another start pattern before finding an 
                        # end pattern.  That probably means emerge died before
                        # finishing what it was doing.
                        # We'll ignore it and continue searching. 
                        break
                    if end_pattern.match(lines[j]):                 
                        # Looks like we found a matching end statement.
                        tokens = lines[j].split()
                        end_time = string.atof((tokens[0])[0:-1])
                        emerge_count += 1
                        total_time = total_time +\
                                (datetime.datetime.fromtimestamp(end_time) -
                                datetime.datetime.fromtimestamp(start_time))
                        break
        if emerge_count > 0:
            return total_time / emerge_count
        else:
            return None          
    except:
        raise BadLogFile, _("Error reading emerge log file.  Check file permissions, or check for corrupt log file.")

def pretend_check(command_string):
    isPretend = (sre.search("--pretend", command_string) != None)
    if not isPretend:
        tmpcmdline = command_string.split()
        #dprint(tmpcmdline)
        for x in tmpcmdline:
            if x[0:1]=="-"and x[1:2]!="-":
                for y in x[1:]:
                    #dprint(y)    
                    if y == "p":
                        #dprint("found it")
                        isPretend = True
    return isPretend

def help_check(command_string):
    return (sre.search("--help", command_string) != None)

def info_check(command_string):
    return (sre.search("emerge info", command_string) != None)

