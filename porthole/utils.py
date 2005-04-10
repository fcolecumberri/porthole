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
    if package and package.is_installed:
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
    if package.upgradable(upgrade_only = True):
        icon = gtk.STOCK_GO_UP
        color = prefs.world_upgradeable_color
    else: # it's a downgrade
        icon = gtk.STOCK_GO_DOWN
        color = prefs.world_downgradeable_color
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
    try: portage = grp.getgrnam("portage")[2]
    except: pass
    return write_access() or (portage in (os.getgroups() + [os.getegid()]))

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
    env["NOCOLOR"] = "true"
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
                                           callback, "_Yes")
        # add "No" button
        self.add_button("_No", 1)
        

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
        if self.upgradeonly: opt_string += '--upgradeonly ' 
        if self.nospinner: opt_string += '--nospinner '
        return opt_string

class PluginOptions:
    """ Holds preferences for plugins """
    def __init__( self, ):
        self.path_list = [os.getcwd()]

class WindowPreferences:
    """ Holds preferences for a window """
    def __init__(self, width = 0, height = 0):
        self.width = width      # width
        self.height = height    # height

class ViewOptions:
	""" Holds foreground colors for a package name"""
	def __init__(self):
		self.world_upgradeable_color = ''
		self.world_downgradeable_color = ''

class GlobalPreferences:
    """Holds some global variables"""
    def __init__(self):
        self.LANG = None

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

        # Main window settings

        try:
           width = dom.getitem('/window/main/width')
        except XMLManagerError:
           width = 200   # Default value
        try:
           height = dom.getitem('/window/main/height')
        except XMLManagerError:
           height = 350   # Default value
        self.main = WindowPreferences(width, height)
        try:
           hpane = dom.getitem('/window/main/hpane')
        except XMLManagerError:
           hpane = 180   # Default value
        self.main.hpane = hpane
        dprint("UTILS: __init__() hpane: %d" %self.main.hpane)
        try:
           vpane = dom.getitem('/window/main/vpane')
        except XMLManagerError:
           vpane = 125   # Default value
        self.main.vpane = vpane
        try:
           search_desc = dom.getitem('/window/main/search_desc')
        except XMLManagerError:
           search_desc = False   # Default value
        self.main.search_desc = search_desc
        try:
           show_nag_dialog = dom.getitem('/window/main/show_nag_dialog')
        except XMLManagerError:
           show_nag_dialog = True   # Default value
        self.main.show_nag_dialog = show_nag_dialog

        # Process window settings

        try:
           width = dom.getitem('/window/process/width')
        except XMLManagerError:
           width = 300   # Default value
        try:
           height = dom.getitem('/window/process/height')
        except XMLManagerError:
           height = 350   # Default value
        self.process = WindowPreferences(width, height)
        try:
           width_verbose = dom.getitem('/window/process/width_verbose')
        except XMLManagerError:
           width_verbose = 500   # Default value
        self.process.width_verbose = width_verbose

        # Terminal window settings

        try:
           width = dom.getitem('/window/terminal/width')
        except XMLManagerError:
           width = 300   # Default value
        try:
           height = dom.getitem('/window/terminal/height')
        except XMLManagerError:
           height = 350   # Default value
        self.terminal = WindowPreferences(width, height)
        try:
           width_verbose = dom.getitem('/window/terminal/width_verbose')
        except XMLManagerError:
           width_verbose = 500   # Default value
        self.terminal.width_verbose = width_verbose
        
        # Formatting tags for the terminal window tabs.  
        # Note: normal font weight = 400 (pango.WEIGHT_NORMAL),
        #       bold = 700 (pango.WEIGHT_BOLD)
        # Note: all colors are in hex for future color editor;
        #       '' means use default color.

        # Caution tag

        self.TAG_DICT = {}
        try:
           forecolor = dom.getitem('/window/terminal/tag/caution/forecolor')
        except XMLManagerError:
           forecolor = ''  # Default value
        try:
           backcolor = dom.getitem('/window/terminal/tag/caution/backcolor')
        except XMLManagerError:
           backcolor = '#ff14b4'  # Default value
        try:
           fontweight = dom.getitem('/window/terminal/tag/caution/fontweight')
        except XMLManagerError:
           fontweight = 400  # Default value
        self.TAG_DICT['caution'] = [forecolor, backcolor, fontweight]

        # Command tag

        try:
           forecolor = dom.getitem('/window/terminal/tag/command/forecolor')
        except XMLManagerError:
           forecolor = '#ffffff'  # Default value
        try:
           backcolor = dom.getitem('/window/terminal/tag/command/backcolor')
        except XMLManagerError:
           backcolor = '#000080'  # Default value
        try:
           fontweight = dom.getitem('/window/terminal/tag/command/fontweight')
        except XMLManagerError:
           fontweight = 700  # Default value
        self.TAG_DICT['command'] = [forecolor, backcolor, fontweight]

        # Emerge tag

        try:
           forecolor = dom.getitem('/window/terminal/tag/emerge/forecolor')
        except XMLManagerError:
           forecolor = ''  # Default value
        try:
           backcolor = dom.getitem('/window/terminal/tag/emerge/backcolor')
        except XMLManagerError:
           backcolor = '#90ee90'  # Default value
        try:
           fontweight = dom.getitem('/window/terminal/tag/emerge/fontweight')
        except XMLManagerError:
           fontweight = 700  # Default value
        self.TAG_DICT['emerge'] = [forecolor, backcolor, fontweight]

        # Error tag

        try:
           forecolor = dom.getitem('/window/terminal/tag/error/forecolor')
        except XMLManagerError:
           forecolor = '#faf0e6'  # Default value
        try:
           backcolor = dom.getitem('/window/terminal/tag/error/backcolor')
        except XMLManagerError:
           backcolor = '#ff0000'  # Default value
        try:
           fontweight = dom.getitem('/window/terminal/tag/error/fontweight')
        except XMLManagerError:
           fontweight = 700  # Default value
        self.TAG_DICT['error'] = [forecolor, backcolor, fontweight]

        # Info tag

        try:
           forecolor = dom.getitem('/window/terminal/tag/info/forecolor')
        except XMLManagerError:
           forecolor = ''  # Default value
        try:
           backcolor = dom.getitem('/window/terminal/tag/info/backcolor')
        except XMLManagerError:
           backcolor = '#b0ffff'  # Default value
        try:
           fontweight = dom.getitem('/window/terminal/tag/info/fontweight')
        except XMLManagerError:
           fontweight = 400  # Default value
        self.TAG_DICT['info'] = [forecolor, backcolor, fontweight]

        # Line number tag 

        try:
           forecolor = dom.getitem('/window/terminal/tag/linenumber/forecolor')
        except XMLManagerError:
           forecolor = '#0000ff'  # Default value
        try:
           backcolor = dom.getitem('/window/terminal/tag/linenumber/backcolor')
        except XMLManagerError:
           backcolor = ''  # Default value
        try:
           fontweight = dom.getitem('/window/terminal/tag/linenumber/fontweight')
        except XMLManagerError:
           fontweight = 700  # Default value
        self.TAG_DICT['linenumber'] = [forecolor, backcolor, fontweight]

        # Note tag

        try:
           forecolor = dom.getitem('/window/terminal/tag/note/forecolor')
        except XMLManagerError:
           forecolor = '#8b008b'  # Default value
        try:
           backcolor = dom.getitem('/window/terminal/tag/note/backcolor')
        except XMLManagerError:
           backcolor = ''  # Default value
        try:
           fontweight = dom.getitem('/window/terminal/tag/note/fontweight')
        except XMLManagerError:
           fontweight = 400  # Default value
        self.TAG_DICT['note'] = [forecolor, backcolor, fontweight]

        # Warning tag

        try:
           forecolor = dom.getitem('/window/terminal/tag/warning/forecolor')
        except XMLManagerError:
           forecolor = ''  # Default value
        try:
           backcolor = dom.getitem('/window/terminal/tag/warning/backcolor')
        except XMLManagerError:
           backcolor = '#eeee80'  # Default value
        try:
           fontweight = dom.getitem('/window/terminal/tag/warning/fontweight')
        except XMLManagerError:
           fontweight = 400  # Default value
        self.TAG_DICT['warning'] = [forecolor, backcolor, fontweight]

        # Run Dialog window settings

        try:
           width = dom.getitem('/window/run_dialog/width')
        except XMLManagerError:
           width = 400   # Default value
        try:
           height = dom.getitem('/window/run_dialog/height')
        except XMLManagerError:
           height = 120   # Default value
        self.run_dialog = WindowPreferences(width, height)
        try:
           history = dom.getitem('/window/run_dialog/history')
        except XMLManagerError:
           # Default value
           history = ["",
                      "emerge ",
                      "ACCEPT_KEYWORDS='~x86' emerge ",
                      "USE=' ' emerge ",
                      "ACCEPT_KEYWORDS='~x86' USE=' ' emerge ",
                      "emerge --help"]
           default_history = len(history)
        self.run_dialog.history = history
        try:
           default_history = dom.getitem('/window/run_dialog/default_history')
        except XMLManagerError:
           # Default value
           # default_history = length of the history items to always remain
           # at the start of the popdown history list & set above when history is set
           default_history = len(history)
        self.run_dialog.default_history = default_history
        try:
           history_length = dom.getitem('/window/run_dialog/history_length')
        except XMLManagerError:
           # Default value for maximum nuber of retained history items
           history_length = 10
        self.run_dialog.history_length = history_length

        # Emerge options
 
        self.emerge = EmergeOptions()
        try:
           self.emerge.pretend = dom.getitem('/emerge/options/pretend')
        except XMLManagerError:
           pass
        try:
           self.emerge.fetch = dom.getitem('/emerge/options/fetch')
        except XMLManagerError:
           pass
        try:
           self.emerge.verbose = dom.getitem('/emerge/options/verbose')
        except XMLManagerError:
           pass
        try:
           self.emerge.upgradeonly = dom.getitem('/emerge/options/upgradeonly')
        except XMLManagerError:
           pass
        try:
           self.emerge.nospinner = dom.getitem('/emerge/options/nospinner')
        except XMLManagerError:
           pass

        # Views config variables

	self.views = ViewOptions()
	#~ try:
		#~ self.views.world_upgradeable_color = dom.getitem('/views/world_upgradeable_color')
	#~ except XMLManagerError:
	self.views.world_upgradeable_color = '' #'green'
	try:
		self.views.world_downgradeable_color = dom.getitem('/views/world_downgradeable_color')
	except XMLManagerError:
		self.views.world_downgradeable_color = 'red'

	# Misc. variables

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
        
        self.plugins = PluginOptions()
        # Load Plugin Preferences
        try:
            new_paths = dom.getitem('/plugins/path_list')
            if new_paths.count(self.plugins.path_list[0]) >= 1:
                self.plugins.path_list = new_paths
            else:
                self.plugins.path_list += new_paths
        except XMLManagerError:
            pass
            
        # Global variables
        self.globals = GlobalPreferences()
        try:
           self.globals.LANG = dom.getitem('/globals/LANG')
        except XMLManagerError:
           self.globals.LANG = 'en'

        # All prefs now loaded or defaulted
        del dom   # no longer needed, release memory


    def save(self):
        """ Save preferences """
        dprint("UTILS: preferences save()")
        dom = XMLManager(None)
        dom.name = 'portholeprefs'
        dom.version = version
        dom.additem('/window/main/width', self.main.width)
        dom.additem('/window/main/height', self.main.height)
        dom.additem('/window/main/hpane', self.main.hpane)
        #dprint("UTILS: save() hpane: %d" %self.main.hpane)
        dom.additem('/window/main/vpane', self.main.vpane)
        dom.additem('/window/main/search_desc', self.main.search_desc)
        dom.additem('/window/main/show_nag_dialog', self.main.show_nag_dialog)
        dom.additem('/window/process/width', self.process.width)
        dom.additem('/window/process/height', self.process.height)
        dom.additem('/window/process/width_verbose', self.process.width_verbose)
        dom.additem('/window/terminal/width', self.terminal.width)
        dom.additem('/window/terminal/height', self.terminal.height)
        dom.additem('/window/terminal/width_verbose', self.terminal.width_verbose)
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
        dom.additem('/views/world_upgradeable_color', self.views.world_upgradeable_color)
        dom.additem('/views/world_downgradeable_color', self.views.world_downgradeable_color)
        dom.additem('/database/size', self.database_size)
        #dprint("UTILS: save(); self.dbtime = %d" %self.dbtime)
        dom.additem('/database/dbtime', self.dbtime)
        dom.additem('/database/dbtotals', self.dbtotals)
        dom.additem('/plugins/path_list', self.plugins.path_list)
        dom.additem('/globals/LANG', self.globals.LANG)
        dom.save(self.__PFILE)
        del dom   # no longer needed, release memory


class PortholeConfiguration:
    """ Holds all of Porthole's developer configurable settings """
    def __init__(self, DATA_PATH):
        dom = XMLManager(DATA_PATH + 'configuration.xml')

        # Handle all the regular expressions.  They will be compiled
        # within this object for the sake of efficiency.

        patternlist = dom.getitem('/re_filters/info')
        self.info_re_list = []
        for regexp in patternlist:
            self.info_re_list.append(sre.compile(regexp))

        patternlist = dom.getitem('/re_filters/notinfo')
        self.info_re_notlist = []
        for regexp in patternlist:
            self.info_re_notlist.append(sre.compile(regexp))

        patternlist = dom.getitem('/re_filters/warning')
        self.warning_re_list = []
        for regexp in patternlist:
            self.warning_re_list.append(sre.compile(regexp))

        patternlist = dom.getitem('/re_filters/notwarning')
        self.warning_re_notlist = []
        for regexp in patternlist:
            self.warning_re_notlist.append(sre.compile(regexp))

        patternlist = dom.getitem('/re_filters/error')
        self.error_re_list = []
        for regexp in patternlist:
            self.error_re_list.append(sre.compile(regexp))

        patternlist = dom.getitem('/re_filters/noterror')
        self.error_re_notlist = []
        for regexp in patternlist:
            self.error_re_notlist.append(sre.compile(regexp))

        patternlist = dom.getitem('/re_filters/caution')
        self.caution_re_list = []
        for regexp in patternlist:
            self.caution_re_list.append(sre.compile(regexp))

        patternlist = dom.getitem('/re_filters/notcaution')
        self.caution_re_notlist = []
        for regexp in patternlist:
            self.caution_re_notlist.append(sre.compile(regexp))

        self.emerge_re = sre.compile(dom.getitem('/re_filters/emerge'))
        self.ebuild_re = sre.compile(dom.getitem('/re_filters/ebuild'))
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
        ''' Parse string, return true if belongs in info tab '''
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
        raise BadLogFile, _("Error reading emerge log file.  Check file " +\
                          "permissions, or check for corrupt log file.")   

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
