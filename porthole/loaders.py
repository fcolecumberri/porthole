#!/usr/bin/env python

'''
    Porthole loader functions
    The main interface the user will interact with

    Copyright (C) 2003 - 2004 Fredrik Arnerup, Brian Dolbec, 
    Daniel G. Taylor and Wm. F. Wheeler

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
import portagelib

from utils import dprint
from gettext import gettext as _

# if using gnome, see if we can import it
try:
    import gnome
    import gnome.vfs
except ImportError:
    # no gnome module, use the standard webbrowser module
    try:
        import webbrowser
    except ImportError:
        print >>stderr, ('Module "webbrowser" not found. '
                     'You will not be able to open web pages.')

# File types dictionary used for logic & loading
Textfile_type = {"changelog": "/ChangeLog", "best_ebuild": ".ebuild", "version_ebuild": ".ebuild"}

def load_textfile(view, package, mode, version = None):
		""" Load and display a text file associated with a package """
		if package:
			dprint(package.full_name)
			if mode != "changelog":
				installed = package.get_installed()
				versions = package.get_versions()
				nonmasked = package.get_versions(include_masked = False)
				if mode == "best_ebuild":
					best = portagelib.best(installed + nonmasked)
					if best == "": # all versions are masked and the package is not installed
						ebuild = package.get_latest_ebuild(True) # get latest masked version
					else:
						ebuild = best
					dprint(ebuild)
					package_file = ('/' + package.full_name + '/' + ebuild.split('/')[1]) + Textfile_type[mode]
				else:
					package_file = ('/' + package.full_name + '/' + package.full_name.split('/')[1] + '-' + version + Textfile_type[mode])
				dprint(package_file)
			else:
				package_file = "/" + package.full_name + Textfile_type[mode]
			try:
				try:
					f = open(portagelib.portdir + package_file)
					data = f.read(); f.close()
				except:
					f = open(portagelib.portdir_overlay + package_file)
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
							view.set_text(_("This ") + Textfile_type[mode][1:] + _(" has an unknown encoding method to porthole \n") + \
										_("Please report this to bugs.gentoo.org and pothole's bugtracker"))
				else:
					view.set_text(Textfile_type[mode][1:] + _(" is Empty"))
			except:
				dprint("LOADERS: Error opening " + Textfile_type[mode][1:] + " for " + package.full_name)
				view.set_text(Textfile_type[mode][1:] + _(" Not Available"))
		else:
			dprint("LOADERS: No package sent to load_textfile()!")
			view.set_text(Textfile_type[mode][1:] + _(" Not Available"))

def load_installed_files(window, view, package):
        """Obtain and display list of installed files for a package,
        if installed."""
        if package:
            installed = package.get_installed()
            is_installed = installed and True or False
            window.set_sensitive(is_installed)
            if is_installed:
                installed.sort()
                installed_files = portagelib.get_installed_files(installed[-1])
                view.set_text(
                    str(len(installed_files)) + _(" installed files:\n\n")
                    + "\n".join(installed_files))
            else:
                view.set_text(_("Not installed"))
        else:
            dprint("LOADERS: No package sent to load_installed_files!")
            view.set_text(_("No data currently available.\n\
                                           The package may not be installed"))

def load_web_page(name):
    """Try to load a web page in the default browser"""
    dprint("LOADERS: load_web_page()")
    browser = web_page(name)
    browser.start()
    return

class web_page(threading.Thread):
    """Try to load a web page in the default browser"""
    def __init__(self, name):
        dprint("LOADERS: web_page.__init__()")
        threading.Thread.__init__(self)
        self.name = name
        self.setDaemon(1)  # quit even if this thread is still running

    def run(self):
        dprint("LOADERS: web_page.run()")
        if self.name == '' or self.name == None:
            return
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


