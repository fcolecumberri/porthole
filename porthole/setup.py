#!/usr/bin/env python

from distutils.core import setup
from version import version

datadir = "porthole/"

setup(name = "porthole",
      version = version,
      description = "GTK+ frontend to Portage",
      author = "Fredrik Arnerup and Daniel G. Taylor",
      # probably a good idea to use these emails
      author_email = ("farnerup@users.sourceforge.net"
                      ", dgt84@users.sourceforge.net"),
      url = "http://porthole.sourceforge.net",
      # py_modules is a list of all our python modules
      py_modules = ["about", "advemerge", "command", "depends",
                    "metadata", "portagelib",
                    "mainwindow", "summary", "terminal",
                    "utils", "version", "version_sort",
                    "views", "xmlmgr"],
      scripts = ["porthole"],
      # data_files is a list of non-python files we need
      # and where to install them
      data_files = [(datadir + "pixmaps",
                     ["pixmaps/porthole-about.png", "pixmaps/porthole-icon.png"]),
		    (datadir + "help",
		     [ "help/advemerge.html", "help/changelog.png", "help/custcmd.html",
		      "help/customize.html", "help/dependencies.png", "help/index.html",
		      "help/install.html", "help/installedfiles.png", "help/mainwindow.html",
		      "help/mainwindow.png", "help/porthole.css", "help/queuetab.png",
		      "help/search.html", "help/summarytab.png", "help/sync.html",
		      "help/termrefs.html", "help/termwindow.png", "help/toc.html",
		      "help/unmerge.html", "help/update.html", "help/warningtab.png"]),
                    (datadir,["porthole.glade", "configuration.xml"]),
                    ("doc/porthole-" + version,
                     ["COPYING", "README", "NEWS", "AUTHORS"]),
                    ("applications", ["porthole.desktop"])
                    ]
      )
