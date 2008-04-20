#!/usr/bin/env python

"""
    Set_config
    A config file saving module for porthole

    Copyright (C) 2005 - 2008 Brian Dolbec, Tommy Iorns

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



import sys
import os

try:
    #import portage
    import portage_const
except ImportError:
    sys.exit(_('Could not find portage module.\n'
         'Are you sure this is a Gentoo system?'))

#debug = False
debug = True
version = 1.0


def dprint(message):
    """Print debug message if debug is true."""
    if debug:
        print message

def set_user_config(filename, name='', ebuild='', add=[], remove=[], delete=[]):
    """
    Adds <name> or '=' + <ebuild> to <filename> with flags <add>.
    If an existing entry is found, items in <remove> are removed and <add> is added.
    
    If <name> and <ebuild> are not given then lines starting with something in
    remove are removed, and items in <add> are added as new lines.
    """
    dprint("SET_CONFIG: set_user_config(): '%s'" % file)
    config_path = portage_const.USER_CONFIG_PATH
    if not os.access(config_path, os.W_OK):
        dprint(" * SET_CONFIG: set_user_config(): no write access to '%s'. " \
              "Perhaps the user is not root?" % config_path)
        return False
    #dprint(" * SET_CONFIG: set_user_config(): filename = " + filename)
    if os.access(filename, os.F_OK): # if file exists
        configfile = open(filename, 'r')
        configlines = configfile.readlines()
        configfile.close()
    else:
        configlines = ['']
    config = [line.split() for line in configlines]
    if not name:
        name =  ebuild
    done = False
    # Check if there is already a line to append to
    for line in config:
        if not line: continue
        dprint("SET_CONFIG: checking line: "  + str(line) )
        if line[0] == name and line[0] not in remove:
            done = True
            dprint("SET_CONFIG: found line for '%s'" % name)
            for flag in remove:
                # just in case there are multiple entries for the same flag
                while flag in line:
                    line.remove(flag)
                    dprint("SET_CONFIG: removed '%s' from line" % flag)
            for flag in add:
                if flag not in line:
                    line.append(flag)
                    dprint("SET_CONFIG: added '%s' to line" % flag)
            if not line[1:]: # if we've removed everything and added nothing
                config[config.index(line)] = []
        elif line[0] in remove:
            config[config.index(line)] = []
            dprint("SET_CONFIG: removed line '%s'" % ' '.join(line))
            done = True
    if not done: # it did not find a matching line to modify
        if "package.use" in filename or "package.keywords" in filename:
            if add:
                config.append([name] + add)
                dprint("SET_CONFIG: added line '%s'" % ' '.join(config[-1]))
            elif ebuild:
                # Probably tried to modify by ebuild but was listed by package.
                # Do a pass with the package name just in case
                pkg = ebuild
                while pkg[0] in ["<",">","=","!","*"]: # remove any leading atoms
                    pkg = pkg[1:]
                import portage
                cplist = portage.catpkgsplit(pkg) or portage.catsplit(pkg)
                dprint("SET_CONFIG: cplist = " + str(cplist))
                if not cplist or len(cplist) < 2:
                    dprint("SET_CONFIG: issues with '%s'" % pkg)
                    return
                cp = cplist[0] + "/" + cplist[1]
                dprint("SET_CONFIG: couldn't find '%s', trying '%s' in stead" % (ebuild, cp))
                return set_user_config(file, name=cp, remove=remove)
        else: # package.mask/unmask: list of names to add
            config.extend([[item] for item in add])
            dprint("SET_CONFIG: added %d lines to %s" % (len(add), file))
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
    return True

def get_make_conf(want_linelist=False, savecopy=False):
    """
    Parses /etc/make.conf into a dictionary of items with
    dict[setting] = properties string
    
    If want_linelist is True, the list of lines read from make.conf will also
    be returned.
    
    If savecopy is true, a copy of make.conf is saved in make.conf.bak.
    """
    dprint("PORTAGELIB: get_make_conf()")
    file = open(portage_const.MAKE_CONF_FILE, 'r')
    if savecopy:
        file2 = open(portage_const.MAKE_CONF_FILE + '.bak', 'w')
        file2.write(file.read())
        file.close()
        file2.close()
        return True
    lines = file.readlines()
    file.close()
    linelist = []
    for line in lines:
        strippedline = line.strip()
        if strippedline.startswith('#'):
            linelist.append([strippedline])
        elif '=' in strippedline:
            splitline = strippedline.split('=', 1)
            if '"' in splitline[0] or "'" in splitline[0]:
                dprint(" * PORTAGELIB: get_make_conf(): couldn't handle line '%s'. Ignoring" % line)
                linelist.append([strippedline])
            else:
                linelist.append(splitline)
            #linelist.append([splitline[0]])
            #linelist[-1].append('='.join(splitline[1:])) # might have been another '='
        else:
            dprint(" * PORTAGELIB: get_make_conf(): couldn't handle line '%s'. Ignoring" % line)
            linelist.append([strippedline])
    dict = {}
    for line in linelist:
        if len(line) == 2:
            dict[line[0]] = line[1].strip('"') # line[1] should be of form '"settings"'
    if want_linelist:
        return dict, linelist
    return dict

def set_make_conf(property, add=[], remove=[], replace=''):
    """
    Sets a variable in make.conf.
    If remove: removes elements of <remove> from variable string.
    If add: adds elements of <add> to variable string.
    If replace: replaces entire variable string with <replace>.
    
    if remove contains the variable name, the whole variable is removed.
    
    e.g. set_make_conf('USE', add=['gtk', 'gtk2'], remove=['-gtk', '-gtk2'])
    e.g. set_make_conf('ACCEPT_KEYWORDS', remove='ACCEPT_KEYWORDS')
    e.g. set_make_conf('PORTAGE_NICENESS', replace='15')
    """
    dprint("SET_CONFIG: set_make_conf()")
    dict, linelist = get_make_conf(True)
    if not property in dict:
        dprint("SET_CONFIG: set_make_conf(): dict does not have key '%s'. Creating..." % property)
        dict[property] = ''
    if not os.access(portage_const.MAKE_CONF_FILE, os.W_OK):
        dprint(" * SET_CONFIG: set_make_conf(): no write access to '%s'. " \
              "Perhaps the user is not root?" % portage_const.MAKE_CONF_FILE)
        return False
    propline = dict[property]
    splitline = propline.split()
    if remove:
        for element in remove:
            while element in splitline:
                splitline.remove(element)
                dprint("SET_CONFIG: removed '%s' from %s" % (element, property))
    if add:
        for element in add:
            if element not in splitline:
                splitline.append(element)
                dprint("SET_CONFIG: added '%s' to %s" % (element, property))
    if replace:
        splitline = [replace]
        dprint("SET_CONFIG: setting %s to '%s'" % (property, replace))
    joinedline = ' '.join(splitline)
    # Now write to make.conf, keeping comments, unparsed lines and line order intact
    done = False
    for line in linelist:
        if line[0].strip() == property:
            if line[0] in remove:
                linelist.remove(line)
                dprint("SET_CONFIG: removed '%s'" % property)
            else:
                line[1] = '"' + joinedline + '"'
            done = True
    if not done:
        while linelist and len(linelist[-1]) == 1 and linelist[-1][0].strip() == '': # blank line
            linelist.pop(-1)
        linelist.append([property, '"' + joinedline + '"'])
        dprint("SET_CONFIG: appended property '%s'" % property)
        linelist.append(['']) # blank line
    joinedlist = ['='.join(line) for line in linelist]
    make_conf = '\n'.join(joinedlist)
    if not make_conf.endswith('\n'):
        make_conf += '\n'
    get_make_conf(savecopy=True) # just saves a copy with ".bak" on the end
    file = open(portage_const.MAKE_CONF_FILE, 'w')
    file.write(make_conf)
    file.close()
    return True


if __name__ == "__main__":

    DATA_PATH = "/usr/share/porthole/"

    from sys import argv, exit, stderr
    from getopt import getopt, GetoptError

    try:
        opts, args = getopt(argv[1:], "lvdf:n:e:a:r:p:R:", ["local", "version", "debug"])
    except GetoptError, e:
        print >>stderr, e.msg
        exit(1)

    file = ""
    name = ""
    ebuild = ""
    add = []
    remove = []
    property = ''
    replace = ''

    for opt, arg in opts:
        dprint(str(opt) + ' ' + str(arg))
        if opt in ('-l', "--local"):
            # running a local version (i.e. not installed in /usr/*)
            DATA_PATH = os.getcwd() + "/"
        elif opt in ('-v', "--version"):
            # print version info
            dprint("set_config.py " + str(version))
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
            add.append(arg)
            dprint("add list = %s" % str(add))
        elif opt in ('-r'):
            remove.append(arg)
            dprint("remove = %s" % str(remove))
        elif opt in ('-p'):
            property = arg
            dprint("property = %s" % str(property))
        elif opt in ('-R'):
            replace = arg
            dprint("replace = %s" % str(replace))
    
    if 'make.conf' in file:
        set_make_conf(property, add, remove, replace)
    else:
        set_user_config(file, name, ebuild, add, remove)
