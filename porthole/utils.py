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

import os
import errno
import string
import sre
import datetime

from sys import stderr
from version import version
from xmlmgr import XMLManager, XMLManagerError

def dprint(message):
    """Print debug message if debug is true."""
    if debug:
        print >>stderr, message

import pygtk; pygtk.require("2.0") # make sure we have the right version
import gtk, portagelib
import os, grp, pwd, cPickle

# if using gnome, see if we can import it
try:
    import gnome
except ImportError:
    # no gnome module, use the standard webbrowser module
    try:
        import webbrowser
    except ImportError:
        print >>stderr, ('Module "webbrowser" not found. '
                     'You will not be able to open web pages.')

def load_web_page(name):
    """Try to load a web page in the default browser"""
    try:
        gnome.url_show(name)
    except:
        try:
            webbrowser.open(name)
        except:
            pass

def get_icon_for_package(package):
    """Return an icon for a package"""
    # if it's installed, find out if it can be upgraded
    if package.is_installed:
        icon = gtk.STOCK_YES
    else:
        # just put the STOCK_NO icon
        icon = gtk.STOCK_NO
    return icon       

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
    HOME = os.getenv("HOME")
    dprint("HOME = " + str(HOME))
    env = {"FEATURES": "notitles",  # Don't try to set the titlebar
            "NOCOLOR": "true",       # and no colours, please
            "HOME":HOME}
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
            self.progbar.set_text("Loading")
            self.progbar.show()
            self.vbox.add(self.progbar)

class EmergeOptions:
    """ Holds common emerge options """
    def __init__(self):
        # let's get some saved values in here!
        self.pretend = False
        self.fetch = False
        self.verbose = False
        self.nospinner = True # currently hidden

    def get_string(self):
        """ Return currently set options in a string """
        opt_string = ' '
        if self.pretend:   opt_string += '--pretend '
        if self.fetch:     opt_string += '--fetchonly '
        if self.verbose:   opt_string += '--verbose '
        if self.nospinner: opt_string += '--nospinner '
        return opt_string

class WindowPreferences:
    """ Holds preferences for a window """
    def __init__(self, width = 0, height = 0):
        self.width = width      # width
        self.height = height    # height


class PortholePreferences:
    """ Holds all of Porthole's user configurable preferences """
    def __init__(self):

        # establish path & name of user prefs file

        home = get_user_home_dir()
        self.__PFILE = home + "/.porthole/prefs.xml"

        # check if directory exists, if not create it
        if not os.access(home + "/.porthole", os.F_OK):
           dprint("~/.porthole does not exist, creating...")
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
           width = 500   # Default value
        try:
           height = dom.getitem('/window/main/height')
        except XMLManagerError:
           height = 650   # Default value
        self.main = WindowPreferences(width, height)
        try:
           hpane = dom.getitem('/window/main/hpane')
        except XMLManagerError:
           hpane = 280   # Default value
        self.main.hpane = hpane
        try:
           vpane = dom.getitem('/window/main/vpane')
        except XMLManagerError:
           vpane = 250   # Default value
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
           width = 400   # Default value
        try:
           height = dom.getitem('/window/process/height')
        except XMLManagerError:
           height = 600   # Default value
        self.process = WindowPreferences(width, height)
        try:
           width_verbose = dom.getitem('/window/process/width_verbose')
        except XMLManagerError:
           width_verbose = 900   # Default value
        self.process.width_verbose = width_verbose

        # Terminal window settings

        try:
           width = dom.getitem('/window/terminal/width')
        except XMLManagerError:
           width = 500   # Default value
        try:
           height = dom.getitem('/window/terminal/height')
        except XMLManagerError:
           height = 400   # Default value
        self.terminal = WindowPreferences(width, height)
        try:
           width_verbose = dom.getitem('/window/terminal/width_verbose')
        except XMLManagerError:
           width_verbose = 900   # Default value
        self.terminal.width_verbose = width_verbose

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
           self.emerge.nospinner = dom.getitem('/emerge/options/nospinner')
        except XMLManagerError:
           pass
        
        # All prefs now loaded or defaulted

        del dom   # no longer needed, release memory


    def save(self):
        """ Save preferences """
        dom = XMLManager(None)
        dom.name = 'portholeprefs'
        dom.version = version
        dom.additem('/window/main/width', self.main.width)
        dom.additem('/window/main/height', self.main.height)
        dom.additem('/window/main/hpane', self.main.hpane)
        dom.additem('/window/main/vpane', self.main.vpane)
        dom.additem('/window/main/search_desc', self.main.search_desc)
        dom.additem('/window/main/show_nag_dialog', self.main.show_nag_dialog)
        dom.additem('/window/process/width', self.process.width)
        dom.additem('/window/process/height', self.process.height)
        dom.additem('/window/process/width_verbose', self.process.width_verbose)
        dom.additem('/window/terminal/width', self.terminal.width)
        dom.additem('/window/terminal/height', self.terminal.height)
        dom.additem('/window/terminal/width_verbose', self.terminal.width_verbose)
        dom.additem('/emerge/options/pretend', self.emerge.pretend)
        dom.additem('/emerge/options/fetch', self.emerge.fetch)
        dom.additem('/emerge/options/verbose', self.emerge.verbose)
        dom.additem('/emerge/options/nospinner', self.emerge.nospinner)
        dom.save(self.__PFILE)
        del dom   # no longer needed, release memory


class PortholeConfiguration:
    """ Holds all of Porthole's developer configurable settings """
    def __init__(self, DATA_PATH):
        dom = XMLManager(DATA_PATH + 'configuration.xml')

        # Handle all the regular expressions.  They will be compiled
        # within this object for the sake of efficiency.

        patternlist = dom.getitem('re_filters/info')
        self.info_re_list = []
        for regexp in patternlist:
            self.info_re_list.append(sre.compile(regexp))

        patternlist = dom.getitem('re_filters/notinfo')
        self.info_re_notlist = []
        for regexp in patternlist:
            self.info_re_notlist.append(sre.compile(regexp))

        patternlist = dom.getitem('re_filters/warning')
        self.warning_re_list = []
        for regexp in patternlist:
            self.warning_re_list.append(sre.compile(regexp))

        patternlist = dom.getitem('re_filters/notwarning')
        self.warning_re_notlist = []
        for regexp in patternlist:
            self.warning_re_notlist.append(sre.compile(regexp))

        patternlist = dom.getitem('re_filters/error')
        self.error_re_list = []
        for regexp in patternlist:
            self.error_re_list.append(sre.compile(regexp))

        patternlist = dom.getitem('re_filters/noterror')
        self.error_re_notlist = []
        for regexp in patternlist:
            self.error_re_notlist.append(sre.compile(regexp))

        patternlist = dom.getitem('re_filters/caution')
        self.caution_re_list = []
        for regexp in patternlist:
            self.caution_re_list.append(sre.compile(regexp))

        patternlist = dom.getitem('re_filters/notcaution')
        self.caution_re_notlist = []
        for regexp in patternlist:
            self.caution_re_notlist.append(sre.compile(regexp))

        self.emerge_re = sre.compile(dom.getitem('re_filters/emerge'))
        self.ebuild_re = sre.compile(dom.getitem('re_filters/ebuild'))
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
        raise BadLogFile, "Error reading emerge log file.  Check file " +\
                          "permissions, or check for corrupt log file."   
