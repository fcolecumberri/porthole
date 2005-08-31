#!/usr/bin/env python

"""
    Set_config
    A config file saving module for porthole

    Copyright (C) 2005 Brian Dolbec, Tommy Iorns

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
"""



from sys import exit
import os
import string

try:
    #import portage
    import portage_const
except ImportError:
    exit(_('Could not find portage module.\n'
         'Are you sure this is a Gentoo system?'))

debug = False
#debug = True
version = 1.0


def dprint(message):
    """Print debug message if debug is true."""
    if debug:
        print >>stderr, message

def set_user_config(file, name='', ebuild='', add=[], remove=[]):
    """
    Adds <name> or '=' + <ebuild> to <file> with flags <add>.
    If an existing entry is found, items in <remove> are removed and <add> is added.
    
    If <name> and <ebuild> are not given then lines starting with something in
    remove are removed, and items in <add> are added as new lines.
    """
    dprint("SET_CONFIG: set_user_config()")
    maskfiles = ['package.mask', 'package.unmask']
    otherfiles = ['package.use', 'package.keywords']
    package_files = otherfiles + maskfiles
    if file not in package_files:
        dprint(" * SET_CONFIG: get_user_config(): unsupported config file '%s'" % file)
        return False
    config_path = portage_const.USER_CONFIG_PATH
    if not os.access(config_path, os.W_OK):
        dprint(" * SET_CONFIG: get_user_config(): no write access to '%s'. " \
              "Perhaps the user is not root?" % config_path)
        return False
    filename = '/'.join([config_path, file])
    if os.access(filename, os.F_OK): # if file exists
        configfile = open(filename, 'r')
        configlines = configfile.readlines()
        configfile.close()
    else:
        configlines = ['']
    config = [line.split() for line in configlines]
    if not name:
        name = '=' + ebuild
    done = False
    # Check if there is already a line to append to
    for line in config:
        if not line: continue
        if line[0] == name:
            done = True
            for flag in remove:
                # just in case there are multiple entries for the same flag
                while flag in line: 
                    line.remove(flag)
            for flag in add:
                if flag not in line:
                    line.append(flag)
            if not line[1:]: # if we've removed everything and added nothing
                config[config.index(line)] = []
        elif line[0] in remove:
            config[config.index(line)] = []
    if not done:
        if name != '=': # package.use/keywords: name or ebuild given
            if add:
                config.append([name] + add)
            elif ebuild:
                # Probably tried to modify by ebuild but was listed by package.
                # Do a pass with the package name just in case
                return set_user_config(file, name=get_full_name(ebuild), remove=remove)
        else: # package.mask/unmask: list of names to add
            config.extend([[item] for item in add])
        done = True
    # remove blank lines
    while [] in config:
        config.remove([])
    while [''] in config:
        config.remove([''])
    # add one blank line to end (so we end with a \n)
    config.append([''])
    configlines = [' '.join(line) for line in config]
    configtext = '\n'.join(configlines)
    configfile = open(filename, 'w')
    configfile.write(configtext)
    configfile.close()
    # This is slow, but otherwise portage doesn't notice the change.
    #reload_portage()
    # Note: could perhaps just update portage.settings.
    # portage.settings.pmaskdict, punmaskdict, pkeywordsdict, pusedict
    # or portage.portdb.mysettings ?
    return True


if __name__ == "__main__":

    DATA_PATH = "/usr/share/porthole/"

    from sys import argv, exit, stderr
    from getopt import getopt, GetoptError

    try:
        opts, args = getopt(argv[1:], "lvdf:n:e:a:r:", ["local", "version", "debug"])
    except GetoptError, e:
        print >>stderr, e.msg
        exit(1)

    file = ""
    name = ""
    ebuild = ""
    add = []
    remove = []

    for opt, arg in opts:
        print opt, arg
        if opt in ('-l', "--local"):
            # running a local version (i.e. not installed in /usr/*)
            DATA_PATH = os.getcwd() + "/"
        elif opt in ('-v', "--version"):
            # print version info
            print "set_config.py " + str(version)
            exit(0)
        elif opt in ('-d', "--debug"):
            debug = True
            dprint("Debug printing is enabled")
        elif opt in ('-f'):
            file = arg
            dprint("file = %s" %file)
        elif opt in ('-n'):
            name = arg
            dprint("name = %s" %name)
        elif opt in ('-e'):
            ebuild = arg
            dprint("ebuild = %s" %ebuild)
        elif opt in ('-a'):
            add = arg.split()
            dprint("add list = %s" %str(add))
        elif opt in ('-r'):
            remove = arg.split()
            dprint("remove = %s" %str(remove))

    set_user_config(file, name, ebuild, add, remove)
