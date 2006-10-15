#!/usr/bin/env python

'''
    Porthole loader functions
    The main interface the user will interact with

    Copyright (C) 2003 - 2005 Fredrik Arnerup, Brian Dolbec, 
    Daniel G. Taylor, Wm. F. Wheeler, Tommy Iorns

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

import os, threading
import errno
import gtk
import utils
from utils import dprint
global PORTAGE
# import the desired portage version
PORTAGE = utils.PORTAGE
#print PORTAGE
if PORTAGE == "pkgcore_lib.py":
    import pkgcore_lib as _portage_lib
else:
    import portagelib as _portage_lib
print ("MAINWINDOW: PORTAGE = %s" %PORTAGE)

from gettext import gettext as _


# if using gnome, see if we can import it
try:
    import gnome
    try:
        import gnomevfs
    except: # try the depricated module
        import gnome.vfs
except ImportError:
    # no gnome module
    #print >>stderr, ('Module "gnome" not found. '
    #                 'You will not be able to use gnome to open web pages.')
    dprint('LOADERS: Module "gnome" not found. '
           'You will not be able to use gnome to open web pages.')
    
# get the standard webbrowser module
try:
    import webbrowser
except ImportError:
    #print >>stderr, ('Module "webbrowser" not found. '
    #                 'You may not be able to open web pages.')
    dprint(' * LOADERS: Module "webbrowser" not found. You may not be able to open web pages.')

# File types dictionary used for logic & loading
Textfile_type = {"changelog": "/ChangeLog", "best_ebuild": ".ebuild", "version_ebuild": ".ebuild"}

def load_textfile(view, package, mode, version = None):
        """ Load and display a text file associated with a package """
        if package:
            dprint("LOADERS; load_textfile(): for '%s'" % package.full_name)
            if mode == "version_ebuild":
                ebuild = version
                dprint("LOADERS; load_textfile(): version_ebuild = " + ebuild)
                package_file = ('/' + package.full_name + '/' + ebuild.split('/')[1]) + Textfile_type[mode]
            elif mode != "changelog":
                installed = package.get_installed()
                versions = package.get_versions()
                nonmasked = package.get_versions(include_masked = False)
                if mode == "best_ebuild":
                    best = _portage_lib.best(installed + nonmasked)
                    if best == "": # all versions are masked and the package is not installed
                        ebuild = package.get_latest_ebuild(True) # get latest masked version
                    else:
                        ebuild = best
                    #dprint("LOADERS; load_textfile(): best_ebuild '%s'" % ebuild)
                    package_file = ('/' + package.full_name + '/' + ebuild.split('/')[1]) + Textfile_type[mode]
                else:
                    dprint("LOADERS: load_textfile(); version = " + version)
                    package_file = ('/' + package.full_name + '/' + package.full_name.split('/')[1] + '-' + version + Textfile_type[mode])
                #dprint("LOADERS: load_textfile(): package file '%s'" % package_file)
            else:
                package_file = "/" + package.full_name + Textfile_type[mode]
                dprint("LOADERS: load_textfile(): package_file = " + package_file)
            try:
                dprint("loaders:load_textfile(); try opening & reading the file")
                if mode == "changelog":
                    try:
                        f = open(_portage_lib.portdir + package_file)
                    except:
                        f = open(_portage_lib.portdir_overlay + package_file)
                elif _portage_lib.is_overlay(ebuild):
                    dprint("LOADERS: load_textfile(); loading from an overlay")
                    f = open(_portage_lib.portdir_overlay + package_file)
                else:
                    dprint("LOADERS: load_textfile(): loading from the portage tree")
                    f = open(_portage_lib.portdir + package_file)
                data = f.read(); f.close()

                if data != None:
                    try:
                        dprint("LOADERS: load_textfile(); trying utf_8 encoding")
                        view.set_text(str(data).decode('utf_8').encode("utf_8",'replace'))
                    except:
                        try:
                            dprint("LOADERS: load_textfile(); trying iso-8859-1 encoding")
                            view.set_text(str(data).decode('iso-8859-1').encode('utf_8', 'replace'))
                        except:
                            dprint("LOADERS: load_textfile(); Failure = unknown encoding")
                            view.set_text(_(
                                "This %s has an encoding method unknown to porthole.\n"
                                "Please report this to bugs.gentoo.org and porthole's bugtracker"
                                ) % Textfile_type[mode][1:])
                else:
                    view.set_text(_("%s is Empty") % Textfile_type[mode][1:])
            except:
                dprint("LOADERS: Error opening " + Textfile_type[mode][1:] + " for " + package.full_name)
                view.set_text(_("%s Not Available") % Textfile_type[mode][1:])
        else:
            dprint("LOADERS: No package sent to load_textfile()!")
            view.set_text(_("%s Not Available") % Textfile_type[mode][1:])

def load_installed_files(window, view, package):
        """Obtain and display list of installed files for a package,
        if installed."""
        if package:
            installed = package.get_installed()
            is_installed = installed and True or False
            window.set_sensitive(is_installed)
            if is_installed:
                installed.sort()
                installed_files = _portage_lib.get_installed_files(installed[-1])
                view.set_text(
                    (_("%i installed files:\n\n") % len(installed_files))
                    + "\n".join(installed_files))
            else:
                view.set_text(_("Not installed"))
        else:
            dprint("LOADERS: No package sent to load_installed_files!")
            view.set_text(_("No data currently available.\n" \
                            "The package may not be installed"))

def load_web_page(name, prefs):
    """Try to load a web page in the default browser"""
    dprint("LOADERS: load_web_page(); starting browser thread")
    browser = web_page(name, prefs)
    browser.start()
    return

def load_help_page(name, prefs):
    """Load a locale-specific help page with the default browser."""
    dprint("LOADERS: load_help_page: %s" % name)
    lc = prefs.globals.LANG
    if not lc: lc = "en"
    helpdir = os.path.join(prefs.DATA_PATH, 'help')
    if os.access(os.path.join(helpdir, lc, name), os.R_OK):
        pagename = "file://" + os.path.join(helpdir, lc, name)
    elif os.access(os.path.join(helpdir, lc.split('_')[0], name), os.R_OK):
        pagename = "file://" + os.path.join(helpdir, lc.split('_')[0], name)
    elif os.access(os.path.join(helpdir, "en", name), os.R_OK):
        pagename = "file://" + os.path.join(helpdir, "en", name)
    else:
        dprint(" * LOADERS: failed to find help file '%s' with LANG='%s'!" %
            (name, prefs.globals.LANG))
        return False
    load_web_page(pagename, prefs)

class web_page(threading.Thread):
    """Try to load a web page in the default browser"""
    def __init__(self, name, prefs):
        dprint("LOADERS: web_page.__init__()")
        threading.Thread.__init__(self)
        self.name = name
        self.prefs = prefs
        self.setDaemon(1)  # quit even if this thread is still running

    def run(self):
        dprint("LOADERS: web_page.run()")
        if self.name == '' or self.name == None:
            return
        if self.prefs.globals.use_custom_browser:
            command = self.prefs.globals.custom_browser_command
            if '%s' not in command: command += ' %s'
            browser = webbrowser.GenericBrowser(command)
            try:
                browser.open(self.name)
            except:
                dprint("LOADERS: failed to open '%s' with browser command '%s'" % (self.name, command))
        else:
            try:
                gnome.url_show(self.name)
            except:
                dprint("LOADERS: Gnome failed trying to open: %s" %self.name)
                try:
                    webbrowser.open(self.name)
                except:
                    dprint("LOADERS: webbrowser failed trying to open: %s  -- giving up" %self.name)
                    pass
        dprint("LOADERS: Browser call_completed for: %s" %self.name)


