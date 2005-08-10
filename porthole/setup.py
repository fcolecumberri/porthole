#!/usr/bin/env python

from distutils.core import setup
from version import version as p_version

datadir = "share/porthole/"

setup( \
    name = "porthole",
    version = p_version,
    description = "GTK+ frontend to Portage",
    author = "Fredrik Arnerup, Daniel G. Taylor, Brian Dolbec, William F. Wheeler",
#    author_email = ("farnerup@users.sourceforge.net", "dgt84@users.sourceforge.net",
#                  "dol-sen@users.sourceforge.net", "tiredoldcoder@users.sourceforge.net"),
    author_email = "farnerup@users.sourceforge.net, dgt84@users.sourceforge.net, " \
                   "dol-sen@users.sourceforge.net, tiredoldcoder@users.sourceforge.net",
    url = "http://porthole.sourceforge.net",
    packages = ['porthole'],
    package_dir = {'porthole':''},
    scripts = ["porthole"],
    data_files = [
        (datadir + "pixmaps",
            ["pixmaps/porthole-about.png", "pixmaps/porthole-icon.png", "porthole.svg"]),
        (datadir + "help",
            ["help/advemerge.html", "help/advemerge.png", "help/changelog.png", "help/custcmd.html",
             "help/custcmd.png", "help/customize.html", "help/dependencies.png", "help/index.html",
             "help/install.html", "help/installedfiles.png", "help/mainwindow.html",
             "help/mainwindow.png", "help/porthole.css", "help/queuetab.png",
             "help/search.html", "help/summarytab.png", "help/sync.html",
             "help/termrefs.html", "help/termwindow.html", "help/termwindow.png", "help/toc.html",
             "help/unmerge.html", "help/update.html", "help/warningtab.png"]),
        (datadir,
            ["advemerge.glade", "porthole.glade", "config.glade", "configuration.xml",
             "dopot.sh", "pocompile.sh"]),
        (datadir + "i18n",
            ["i18n/messages.pot", "i18n/vi.po", "i18n/fr_FR.po", "i18n/de_DE.po",
             "i18n/pl.po", "i18n/ru.po"]),
        ("share/applications", ["porthole.desktop"]),
        ("share/pixmaps", ["pixmaps/porthole-icon.png"]),
        (datadir + "plugins", ["plugins/__init__.py"])
    ]
)
