#!/usr/bin/env python

from distutils.core import setup
#pull the version directly from porthole
from utils import version

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
      py_modules = ["about", "depends", "metadata",
                    "portagelib", "process",
                    "mainwindow", "summary", "utils"],
      scripts = ["porthole"],
      # data_files is a list of non-python files we need
      # and where to install them
      data_files = [(datadir + "pixmaps",
                     ["pixmaps/porthole-about.png",
                      "pixmaps/porthole-icon.png"]),
                    (datadir,
                     ["porthole.glade"]),
                    ("doc/porthole-" + version, ["COPYING"])
                    ]
     )
