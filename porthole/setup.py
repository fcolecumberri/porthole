#!/usr/bin/env python

#import distutils
from distutils.core import setup
#pull the version directly from porthole
from porthole import version

setup(name = "Porthole",
      version = version,
      description = "GTK+ frontend to Portage",
      author = "Fredrik Arnerup and Daniel G. Taylor",
      # probably a good idea to use these emails
      author_email = "farnerup@users.sourceforge.net"\
                     ", dgt84@users.sourceforge.net",
      url = "http://porthole.sourceforge.net",
      # py_modules is a list of all our python modules
      py_modules = ["about", "depends", "metadata",
                    "portagelib", "porthole", "process",
                    "summary", "utils"],
      # data_files is a list of non-python files we need
      # and where to install them
      data_files = [("pixmaps",
                    ["pixmaps/porthole-about.png",
                    "pixmaps/porthole-icon.png"]),
                    ("",
                    ["porthole.glade"])]
     )
