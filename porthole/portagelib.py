#!/usr/bin/env python

"""
    PortageLib
    An interface library to Gentoo's Portage

    Copyright (C) 2003 - 2006 Fredrik Arnerup, Daniel G. Taylor,
    Wm. F. Wheeler, Brian Dolbec, Tommy Iorns

    Copyright(c) 2004, Karl Trygve Kalleberg <karltk@gentoo.org>
    Copyright(c) 2004, Gentoo Foundation

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

from utils import dprint, dsave, is_root
from sys import exit, stderr
import os
from gettext import gettext as _
from sterminal import SimpleTerminal
from dispatcher import Dispatcher
import version_sort

try:
    import portage
    import portage_const
    print >>stderr, ("PORTAGELIB: portage version = " + portage.VERSION)
except ImportError:
    exit(_('Could not find portage module.\n'
         'Are you sure this is a Gentoo system?'))
         
#from gentoolkit import package as gen_Package

import threading

if is_root: # then import some modules and run it directly
    import set_config


from metadata import parse_metadata

thread_id = os.getpid()

def reload_portage():
    dprint('PORTAGELIB: reloading portage')
    dprint("PORTAGELIB: old portage version = " + portage.VERSION)
    reload(portage)
    dprint("PORTAGELIB: new portage version = " + portage.VERSION)


def get_world():
        world = []
        try:
            file = open("/var/lib/portage/world", "r")
            world = file.read().split()
            file.close()
        except:
            dprint("PORTAGELIB: get_world(); Failure to locate file: '/var/lib/portage/world'")
            dprint("PORTAGELIB: get_world(); Trying '/var/cache/edb/world'")
            try:
                file = open("/var/cache/edb/world", "r")
                world = file.read().split()
                file.close()
                dprint("PORTAGELIB: get_world(); OK")
            except:
                dprint("PORTAGELIB: get_world(); Failed to locate the world file")
        return world

World = get_world()

# And now for some code stolen from pkgcore :)
# Copyright: 2005 Brian Harring <ferringb@gmail.com>
# License: GPL2
def iter_read_bash(bash_source):
	"""read file honoring bash commenting rules.  Note that it's considered good behaviour to close filehandles, as such, 
	either iterate fully through this, or use read_bash instead.
	once the file object is no longer referenced, the handle will be closed, but be proactive instead of relying on the 
	garbage collector."""
	if isinstance(bash_source, basestring):
		bash_source = open(bash_source, 'r')
	for s in bash_source:
		s=s.strip()
		if s.startswith("#") or s == "":
			continue
		yield s
	bash_source.close()

def read_bash(bash_source):
	return list(iter_read_bash(bash_source))
# end of stolen code

def get_sets_list( filename ):
    """Get the package list file and turn it into a tuple
       attributes: pkgs[key = full_name] = [atoms, version]"""
    pkgs = {}
    try:
        list = read_bash(filename)
    except:
        dprint("PORTAGELIB: get_sets_list(); Failure to locate file: %s" %filename)
        return None
    # split the atoms from the pkg name and any trailing attributes if any
    for item in list:
        parts = split_atom_pkg(item)
        pkgs[parts[0]] = parts[1:]
    return pkgs

def split_atom_pkg( pkg ):
    """Extract [category/package, atoms, version] from some ebuild identifier"""
    atoms = []
    version = ''
    if pkg.endswith("*"): pkg = pkg[:-1]
    cplist = portage.catpkgsplit(pkg) or portage.catsplit(pkg)
    if not cplist or len(cplist) < 2:
        dprint("PORTAGELIB split_pkg(): issues with '%s'" % pkg)
        return ['', '', '']
    cp = cplist[0] + "/" + cplist[1]
    while cp[0] in ["<",">","=","!","*"]:
        atoms.append(cp[0])
        cp = cp[1:]
    if cplist:
        version = cplist[2]
        if cplist[3] != 'r0':
            version += '-' + cplist[3]
    return [str(cp), atoms.join(), version] # hmm ... unicode keeps appearing :(


def reload_world():
    dprint("PORTAGELIB: reset_world();")
    global World
    World = get_world()


def get_use_flag_dict():
    """ Get all the use flags and return them as a dictionary 
        key = use flag forced to lowercase
        data = list[0] = 'local' or 'global'
               list[1] = 'package-name'
               list[2] = description of flag   
    """
    dict = {}

    # process standard use flags

    List = portage.grabfile('/usr/portage/profiles/use.desc')
    for item in List:
        index = item.find(' - ')
        dict[item[:index].strip().lower()] = ['global', '', item[index+3:]]

    # process local (package specific) use flags

    List = portage.grabfile('/usr/portage/profiles/use.local.desc')
    for item in List:
        index = item.find(' - ')
        data = item[:index].lower().split(':')
        try: # got this error starting porthole==> added code to catch it, but it works again???
##            big_squirt porthole # ./porthole -l -d
##
##            ** (porthole:23062): WARNING **: `GtkTextSearchFlags' is not an enum type
##            Traceback (most recent call last):
##              File "./porthole", line 45, in ?
##                from mainwindow import MainWindow
##              File "/home/brian/porthole/mainwindow.py", line 28, in ?
##                import portagelib, os, string
##              File "/home/brian/porthole/portagelib.py", line 73, in ?
##                UseFlagDict = get_use_flag_dict()
##              File "/home/brian/porthole/portagelib.py", line 69, in get_use_flag_dict
##                dict[data[1].strip()] = ['local', data[0].strip(), item[index+3:]]
##            IndexError: list index out of range
##            big_squirt porthole # ./porthole -l -d
##
            dict[data[1].strip()] = ['local', data[0].strip(), item[index+3:]]
        except:
            dprint("PORTAGELIB: get_use_flag_dict(); error in index??? data[0].strip, item[index:]")
            dprint(data[0].strip())
            dprint(item[index:])
    return dict

# Run it once for sake of efficiency
UseFlagDict = get_use_flag_dict()
# debug code follows WFW
#polibkeys = UseFlagDict.keys()
#polibkeys.sort()
#for polibkey in polibkeys:
#    print polibkey, ':', UseFlagDict[polibkey]
    
def get_portage_environ(var):
    """Returns environment variable from portage if possible, else None"""
    try: temp = portage.config(clone=portage.settings).environ()[var]
    except: temp = None
    return temp

settings = portage.config(clone=portage.settings)
portdir = portage.config(clone=portage.settings).environ()['PORTDIR']
# is PORTDIR_OVERLAY always defined?
portdir_overlay = get_portage_environ('PORTDIR_OVERLAY')

ACCEPT_KEYWORDS = get_portage_environ("ACCEPT_KEYWORDS")

# Run it once for sake of efficiency
SystemUseFlags = get_portage_environ("USE").split()

# did not work.  need to reload portage
def reset_use_flags():
    dprint("PORTAGELIB: reset_use_flags();")
    global SystemUseFlags
    SystemUseFlags = get_portage_environ("USE").split()

virtuals = portage.settings.virtuals

# lower case is nicer
keys = [key.lower() for key in portage.auxdbkeys]

# establish a semaphore for the Database
Installed_Semaphore = threading.Semaphore()

# a list of all installed packages
Installed_Semaphore.acquire()
installed = None
Installed_Semaphore.release()

def get_arch():
    """Return host CPU architecture"""
    return portage.settings["ARCH"]

def get_name(full_name):
    """Extract name from full name."""
    return full_name.split('/')[1]

def pkgsplit(ebuild):
    """Split ebuild into [category/package, version, release]"""
    dprint("PORTAGELIB: pkgsplit(); calling portage function")
    return portage.pkgsplit(ebuild)

def get_category(full_name):
    """Extract category from full name."""
    return full_name.split('/')[0]

def get_full_name(ebuild):
    """Extract category/package from some ebuild identifier"""
    if ebuild.endswith("*"): ebuild = ebuild[:-1]
    cplist = portage.catpkgsplit(ebuild) or portage.catsplit(ebuild)
    if not cplist or len(cplist) < 2:
        dprint("PORTAGELIB get_full_name(): issues with '%s'" % ebuild)
        return ''
    cp = cplist[0] + "/" + cplist[1]
    while cp[0] in ["<",">","=","!","*"]: cp = cp[1:]
    return str(cp) # hmm ... unicode keeps appearing :(

def get_installed(package_name):
    """Extract installed versions from package_name.
    package_name can be the short package name ('eric'), long package name ('dev-util/eric')
    or a version-matching string ('>=dev-util/eric-2.5.1')
    """
    return portage.db['/']['vartree'].dep_match(str(package_name))

def xmatch(*args, **kwargs):
    """Pass arguments on to portage's caching match function.
    xmatch('match-all',package-name) returns all ebuilds of <package-name> in a list,
    xmatch('match-visible',package-name) returns non-masked ebuilds,
    xmatch('match-list',package-name,mylist=list) checks for <package-name> in <list>
    There are more possible arguments.
    package-name may be, for example:
       gnome-base/control-center            ebuilds for gnome-base/control-center
       control-center                       ebuilds for gnome-base/control-center
       >=gnome-base/control-center-2.8.2    only ebuilds with version >= 2.8.2
    """
    return portage.portdb.xmatch(*args, **kwargs)

def get_user_config(file, name=None, ebuild=None):
    """
    Function for parsing package.use, package.mask, package.unmask
    and package.keywords.
    
    Returns /etc/portage/<file> as a dictionary of ebuilds, with
    dict[ebuild] = list of flags.
    If name is given, it will be parsed for ebuilds with xmatch('match-all'),
    and only those ebuilds will be returned in dict.
    
    If <ebuild> is given, it will be matched against each line in <file>.
    For package.use/keywords, a list of applicable flags is returned.
    For package.mask/unmask, a list containing the matching lines is returned.
    """
    dprint("PORTAGELIB: get_user_config('%s')" % file)
    maskfiles = ['package.mask', 'package.unmask']
    otherfiles = ['package.use', 'package.keywords']
    package_files = otherfiles + maskfiles
    if file not in package_files:
        dprint(" * PORTAGELIB: get_user_config(): unsupported config file '%s'" % file)
        return None
    filename = '/'.join([portage_const.USER_CONFIG_PATH, file])
    if not os.access(filename, os.F_OK):
        dprint(" * PORTAGELIB: get_user_config(): file does not exist: '%s'?" % file)
        return [] #None
    else:
        if not os.access(filename, os.R_OK):
            dprint(" * PORTAGELIB: get_user_config(): no read access on '%s'?" % file)
            return [] #None
    configfile = open(filename, 'r')
    configlines = configfile.readlines()
    configfile.close()
    config = [line.split() for line in configlines]
    # e.g. [['media-video/mplayer', 'real', '-v4l'], [app-portage/porthole', 'sudo']]
    dict = {}
    if ebuild is not None:
        result = []
        for line in config:
            if line and line[0]:
                if line[0].startswith('#'):
                    continue
                match = xmatch('match-list', line[0], mylist=[ebuild])
                if match:
                    if file in maskfiles: result.extend(line[0]) # package.mask/unmask
                    else: result.extend(line[1:]) # package.use/keywords
        return result
    if name:
        target = xmatch('match-all', name)
        for line in config:
            if line and line[0]:
                if line[0].startswith('#'):
                    continue
                ebuilds = xmatch('match-all', line[0])
                for ebuild in ebuilds:
                    if ebuild in target:
                        dict[ebuild] = line[1:]
    else:
        for line in config:
            if line and line[0]:
                if line[0].startswith('#'):
                    continue
                ebuilds = xmatch('match-all', line[0])
                for ebuild in ebuilds:
                    dict[ebuild] = line[1:]
    return dict

def set_user_config(prefs, file, name='', ebuild='', add='', remove='', callback=None):
    """
    Adds <name> or '=' + <ebuild> to <file> with flags <add>.
    If an existing entry is found, items in <remove> are removed and <add> is added.
    
    If <name> and <ebuild> are not given then lines starting with something in
    remove are removed, and items in <add> are added as new lines.
    """
    dprint("PORTAGELIB: set_user_config()")
    command = ''
    maskfiles = ['package.mask', 'package.unmask']
    otherfiles = ['package.use', 'package.keywords']
    package_files = otherfiles + maskfiles
    if file not in package_files:
        dprint(" * PORTAGELIB: set_user_config(); unsupported config file '%s'" % file)
        return False
    if isinstance(add, list):
        add = ' '.join(add)
    if isinstance(remove, list):
        remove = ' '.join(remove)
    config_path = portage_const.USER_CONFIG_PATH
    if not os.access(config_path, os.W_OK):
        commandlist = [prefs.globals.su, '"python', prefs.DATA_PATH + 'set_config.py -d -f %s' %file]
        if name != '':
            commandlist.append('-n %s' %name)
        if ebuild != '':
            commandlist.append('-e %s' %ebuild)
        if add != '':
            items = add.split()
            for item in items:
                commandlist.append('-a %s' % item)
        if remove != '':
            items = remove.split()
            for item in items:
                commandlist.append('-r %s' % item)
        command = ' '.join(commandlist) + '"'
        dprint(" * PORTAGELIB: set_user_config(); command = %s" %command )
        if not callback: callback = reload_portage
        app = SimpleTerminal(command, False, dprint_output='SET_USER_CONFIG CHILD APP: ', callback=Dispatcher(callback))
        app._run()
    else:
        add = add.split()
        remove = remove.split()
        set_config.set_user_config(file, name, ebuild, add, remove)
        if callback: callback()
        else: reload_portage()
    # This is slow, but otherwise portage doesn't notice the change.
    #reload_portage()
    # Note: could perhaps just update portage.settings.
    # portage.settings.pmaskdict, punmaskdict, pkeywordsdict, pusedict
    # or portage.portdb.mysettings ?
    return True

#~ def set_user_config(file, name='', ebuild='', add=[], remove=[]):
    #~ """
    #~ Adds <name> or '=' + <ebuild> to <file> with flags <add>.
    #~ If an existing entry is found, items in <remove> are removed and <add> is added.
    
    #~ If <name> and <ebuild> are not given then lines starting with something in
    #~ remove are removed, and items in <add> are added as new lines.
    #~ """
    #~ dprint("PORTAGELIB: set_user_config()")
    #~ if isinstance(add, basestring):
        #~ add = [add]
    #~ if isinstance(remove, basestring):
        #~ remove = [remove]
    #~ maskfiles = ['package.mask', 'package.unmask']
    #~ otherfiles = ['package.use', 'package.keywords']
    #~ package_files = otherfiles + maskfiles
    #~ if file not in package_files:
        #~ dprint(" * PORTAGELIB: get_user_config(): unsupported config file '%s'" % file)
        #~ return False
    #~ config_path = portage_const.USER_CONFIG_PATH
    #~ if not os.access(config_path, os.W_OK):
        #~ dprint(" * PORTAGELIB: get_user_config(): no write access to '%s'. " \
              #~ "Perhaps the user is not root?" % config_path)
        #~ return False
    #~ filename = '/'.join([config_path, file])
    #~ if os.access(filename, os.F_OK): # if file exists
        #~ configfile = open(filename, 'r')
        #~ configlines = configfile.readlines()
        #~ configfile.close()
    #~ else:
        #~ configlines = ['']
    #~ config = [line.split() for line in configlines]
    #~ if not name:
        #~ name = '=' + ebuild
    #~ done = False
    #~ # Check if there is already a line to append to
    #~ for line in config:
        #~ if not line: continue
        #~ if line[0] == name:
            #~ done = True
            #~ for flag in remove:
                #~ if flag in line:
                    #~ line.remove(flag)
            #~ for flag in add:
                #~ if flag not in line:
                    #~ line.append(flag)
            #~ if not line[1:]: # if we've removed everything and added nothing
                #~ config[config.index(line)] = []
        #~ elif line[0] in remove:
            #~ config[config.index(line)] = []
    #~ if not done:
        #~ if name != '=': # package.use/keywords: name or ebuild given
            #~ if add:
                #~ config.append([name] + add)
            #~ elif ebuild:
                #~ # Probably tried to modify by ebuild but was listed by package.
                #~ # Do a pass with the package name just in case
                #~ return set_user_config(file, name=get_full_name(ebuild), remove=remove)
        #~ else: # package.mask/unmask: list of names to add
            #~ config.extend([[item] for item in add])
        #~ done = True
    #~ # remove blank lines
    #~ while [] in config:
        #~ config.remove([])
    #~ while [''] in config:
        #~ config.remove([''])
    #~ # add one blank line to end (so we end with a \n)
    #~ config.append([''])
    #~ configlines = [' '.join(line) for line in config]
    #~ configtext = '\n'.join(configlines)
    #~ configfile = open(filename, 'w')
    #~ configfile.write(configtext)
    #~ configfile.close()
    #~ # This is slow, but otherwise portage doesn't notice the change.
    #~ reload_portage()
    #~ # Note: could perhaps just update portage.settings.
    #~ # portage.settings.pmaskdict, punmaskdict, pkeywordsdict, pusedict
    #~ # or portage.portdb.mysettings ?
    #~ return True

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

def set_make_conf(prefs, property, add='', remove='', replace='', callback=None):
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
    dprint("PORTAGELIB: set_make_conf()")
    command = ''
    file = 'make.conf'
    if isinstance(add, list):
        add = ' '.join(add)
    if isinstance(remove, list):
        remove = ' '.join(remove)
    if isinstance(replace, list):
        replace = ' '.join(replace)
    config_path = portage_const.USER_CONFIG_PATH
    if not os.access(portage_const.MAKE_CONF_FILE, os.W_OK):
        command = (prefs.globals.su + ' "python ' + prefs.DATA_PATH + 'set_config.py -d -f %s ' %file)
        command = (command + '-p %s ' % property)
        if add != '':
            command = (command + '-a %s ' %("'" + add + "'"))
        if remove != '':
            command = (command + '-r %s' %("'" + remove + "'"))
        command = command + '"'
        dprint(" * PORTAGELIB: set_make_conf(); command = %s" %command )
        if not callback: callback = reload_portage
        app = SimpleTerminal(command, False, dprint_output='SET_MAKE_CONF CHILD APP: ', callback=Dispatcher(callback))
        app._run()
    else:
        add = add.split()
        remove = remove.split()
        set_config.set_make_conf(property, add, remove, replace)
        if callback: callback()
        else: reload_portage()
    # This is slow, but otherwise portage doesn't notice the change.
    #reload_portage()
    # Note: could perhaps just update portage.settings.
    # portage.settings.pmaskdict, punmaskdict, pkeywordsdict, pusedict
    # or portage.portdb.mysettings ?
    return True

def get_version(ebuild):
    """Extract version number from ebuild name"""
    result = ''
    parts = portage.catpkgsplit(ebuild)
    if parts:
        result = parts[2]
        if parts[3] != 'r0':
            result += '-' + parts[3]
    return result

def extract_package(ebuild):
    """Returns cat/package from cat/package-ebuild,
       or None if input is not in that format.  """
    result = None
    parts = portage.catpkgsplit(ebuild)
    if parts:
        result = "/".join(parts[0:2])
    return result

def get_installed_files(ebuild):
    """Get a list of installed files for an ebuild, assuming it has
    been installed."""
    path = "/var/db/pkg/" + ebuild + "/CONTENTS"
    files = []
    try:
        # hoping some clown won't use spaces in filenames ...
        files = [line.split()[1].decode('ascii')
                 for line in open(path, "r").readlines()]
    except: pass
    files.sort()
    return files

# this is obsolete
def get_property(ebuild, property):
    """Read a property of an ebuild. Returns a string."""
    # portage.auxdbkeys contains a list of properties
    if portage.portdb.cpv_exists(ebuild): # if in portage tree
        return portage.portdb.aux_get(ebuild, [property])[0]
    else:
        vartree = portage.db['/']['vartree']
        if vartree.dbapi.cpv_exists(ebuild): # elif in installed pkg tree
            return vartree.dbapi.aux_get(ebuild, [property])[0]
        else: return ''

def best(versions):
    """returns the best version in the list"""
    return portage.best(versions)

def get_archlist():
    """lists the architectures accepted by portage as valid keywords"""
    list = portage.archlist[:]
    for entry in list:
        if entry.startswith("~"):
            list.remove(entry)
    return list

def get_masking_reason(ebuild):
    """Strips trailing \n from, and returns the masking reason given by portage"""
    reason = portage.getmaskingreason(ebuild)
    if not reason: return _('No masking reason given')
    if reason.endswith("\n"):
        reason = reason[:-1]
    return reason

class Properties:
    """Contains all variables in an ebuild."""
    def __init__(self, dict = None):
        self.__dict = dict
        #dprint("PORTAGELIB: Properties=")
        #dprint(dict)
        
    def __getattr__(self, name):
        try: return self.__dict[name]
        except: return ''
        
    def get_slot(self):
        """Return ebuild slot"""
        return self.slot

    def get_keywords(self):
        """Returns a list of strings."""
        return self.keywords.split()

    def get_use_flags(self):
        """Returns a list of strings."""
        return self.iuse.split()

    def get_homepages(self):
        """Returns a list of strings."""
        return self.homepage.split()

def get_size(ebuild):
    """ Returns size of package to fetch. """
    #This code to calculate size of downloaded files was taken from /usr/bin/emerge - BB
    mydigest = portage.db['/']['porttree'].dbapi.finddigest(ebuild)
    mysum = 0
    try:
        myfile = open(mydigest,"r")
        for line in myfile.readlines():
            mysum += int(line.split(" ")[3])
        myfile.close()
        mystr = str(mysum/1024)
        mycount=len(mystr)
        while (mycount > 3):
            mycount-=3
            mystr=mystr[:mycount]+","+mystr[mycount:]
        mysum=mystr+" kB"
    except SystemExit, e:
        raise # Needed else can't exit
    except Exception, e:
        dprint( "PORTAGELIB: get_size; Exception: %s" %s  )
        dprint( "PORTAGELIB: get_size; ebuild: " + str(ebuild))
        dprint( "PORTAGELIB: get_size; mydigest: " + str(mydigest))
        mysum="[bad / blank digest]"
    return mysum

def get_digest(ebuild):
    """Returns digest of an ebuild"""
    mydigest = portage.db['/']['porttree'].dbapi.finddigest(ebuild)
    digest_file = []
    try:
        myfile = open(mydigest,"r")
        for line in myfile.readlines():
            digest_file.append(line.split(" "))
        myfile.close()
    except SystemExit, e:
        raise # Needed else can't exit
    except Exception, e:
        dprint("PORTAGELIB: get_digest(): Exception: %s" % e)
    return digest_file

def get_properties(ebuild):
    """Get all ebuild variables in one chunk."""
    ebuild = str(ebuild) #just in case
    if portage.portdb.cpv_exists(ebuild): # if in portage tree
        try:
            return Properties(dict(zip(keys, portage.portdb.aux_get(ebuild, portage.auxdbkeys))))
        except IOError, e: # Sync being performed may delete files
            dprint(" * PORTAGELIB: get_properties(): IOError: %s" % e)
            return Properties()
    else:
        vartree = portage.db['/']['vartree']
        if vartree.dbapi.cpv_exists(ebuild): # elif in installed pkg tree
            return Properties(dict(zip(keys, vartree.dbapi.aux_get(ebuild, portage.auxdbkeys))))
        else: return Properties()

def is_overlay(cpv): # lifted from gentoolkit
    """Returns true if the package is in an overlay."""
    dir,ovl = portage.portdb.findname2(cpv)
    return ovl != portdir

def get_overlay(cpv):
    """Returns an overlay."""
    dir,ovl = portage.portdb.findname2(cpv)
    return ovl

    
def get_metadata(package):
    """Get the metadata for a package"""
    # we could check the overlay as well,
    # but we are unlikely to find any metadata files there
    try: return parse_metadata(portdir + "/" + package + "/metadata.xml")
    except: return None

def get_system_pkgs(): # lifted from gentoolkit
	"""Returns a tuple of lists, first list is resolved system packages,
	second is a list of unresolved packages."""
	pkglist = settings.packages
	resolved = []
	unresolved = []
	for x in pkglist:
		cpv = x.strip()
		if len(cpv) and cpv[0] == "*":
			pkg = find_best_match(cpv)
			if pkg:
				resolved.append(get_full_name(pkg))
			else:
				unresolved.append(get_full_name(cpv))
	return (resolved + unresolved)


def find_best_match(search_key): # lifted from gentoolkit
    """Returns a Package object for the best available installed candidate that
    matched the search key. Doesn't handle virtuals perfectly"""
    # FIXME: How should we handle versioned virtuals??
    dprint("PORTAGELIB: find_best_match(search_key)=" + search_key)
    cat,pkg,ver,rev = split_package_name(search_key)
    if cat == "virtual":
        t = portage.db["/"]["vartree"].dep_bestmatch(cat+"/"+pkg)
    else:
        t = portage.db["/"]["vartree"].dep_bestmatch(search_key)
    if t:
        return t
    return None

def split_package_name(name): # lifted from gentoolkit, handles vituals for find_best_match()
	"""Returns a list on the form [category, name, version, revision]. Revision will
	be 'r0' if none can be inferred. Category and version will be empty, if none can
	be inferred."""
	r = portage.catpkgsplit(name)
	if not r:
		r = name.split("/")
		if len(r) == 1:
			return ["", name, "", "r0"]
		else:
			return r + ["", "r0"]
	if r[0] == 'null':
		r[0] = ''
	return r


class Package:
    """An entry in the package database"""

    def __init__(self, full_name):
        self.full_name = str(full_name) # unicode gives portage headaches
        self.latest_ebuild = None
        self.hard_masked = None
        self.hard_masked_nocheck = None
        self.best_ebuild = None
        self.installed_ebuilds = None
        self.name = None
        self.category = None
        self.properties = {}
        self.upgradable = None

        self.latest_installed = None
        self.size = None
        self.digest_file = None
        self.in_world = full_name in World
        self.is_checked = False

    def in_list(self, list=None):
        """returns True/False if the package is listed in the list"""
        #dprint("Package.in_list: %s" %self.full_name)
        #dprint("Package.in_list: %s" %str(list))
        if self.full_name == "None":
            return False
        if list == "World":
            return self.in_world
        elif list == "Dependencies":
            #  redundant I know, but this method leaves room for adding an "Orphaned"  listing next
            return not self.in_world
        elif list:
            #dprint("Package.in_list: %s" %(self.full_name in list))
            # insert routine for checking the if the package is in the specified list
            return self.full_name in list
        return False
            

    def update_info(self):
        """Update the package info"""
        if self.full_name == "None":
            return
        self.latest_installed == None
        Installed_Semaphore.acquire()
        self.is_installed = full_name in installed  # true if installed
        Installed_Semaphore.release()
        self.in_world = full_name in World

    def get_installed(self):
        """Returns a list of all installed ebuilds."""
        if self.full_name == "None":
            return []
        if self.installed_ebuilds == None:
            self.installed_ebuilds = get_installed(self.full_name)
        return self.installed_ebuilds
    
    def get_name(self):
        """Return name portion of a package"""
        if self.full_name == "None":
            return self.full_name
        if self.name == None:
            self.name = get_name(self.full_name)
        return self.name

    def get_category(self):
        """Return category portion of a package"""
        if self.full_name == "None":
            return ''
        if self.category == None:
            self.category = get_category(self.full_name)
        return self.category

    def get_latest_ebuild(self, include_masked = False):
        """Return latest ebuild of a package"""
        # Note: this is slow, see get_versions()
        # Note: doesn't return hard-masked packages by default, unless in package.unmask
        # unstable packages however ARE returned. To return the best version for a system,
        # taking into account keywords and masking, use get_best_ebuild().
        if self.full_name == "None":
            return ''
        if include_masked:
            return portage.best(self.get_versions())
        if self.latest_ebuild == None:
            vers = self.get_versions()
            #dprint("PORTAGELIB: get_latest_ebuild; vers = %s" %str(vers)) 
            for m in self.get_hard_masked(check_unmask = True):
                while m in vers:
                    vers.remove(m)
            self.latest_ebuild = portage.best(vers)
        return self.latest_ebuild

    def get_best_ebuild(self):
        """Return best visible ebuild (taking account of package.keywords, .mask and .unmask.
        If all ebuilds are masked for your architecture, returns ''."""
        if self.full_name == "None":
            return ''
        if self.best_ebuild == None:
            self.best_ebuild = portage.portdb.xmatch("bestmatch-visible",str(self.full_name)) # no unicode
        return self.best_ebuild

    def get_default_ebuild(self):
        if self.full_name == "None":
            return ''
        return (self.get_best_ebuild() or
                self.get_latest_ebuild() or
                self.get_latest_ebuild(include_masked = True) or
                self.get_latest_installed())

    def get_size(self):
        if self.full_name == "None":
            return ''
        if self.size == None:
            ebuild = self.get_default_ebuild()
            if ebuild: self.size = get_size(ebuild)
            else: self.size = ''
        return self.size

    def get_digest(self):
        if self.full_name == "None":
            return ''
        if self.digest_file == None:
            self.digest_file = get_digest( self.get_latest_ebuild() )
        return self.digest_file

    def get_latest_installed(self):
        if self.full_name == "None":
            return ''
        if self.latest_installed == None:
            installed_ebuilds = self.get_installed( )
            if len(installed_ebuilds) == 1:
                return installed_ebuilds[0]
            elif len(installed_ebuilds) == 0:
                return ""
            installed_ebuilds = version_sort.ver_sort( installed_ebuilds )
            self.latest_installed = installed_ebuilds[-1]
        return self.latest_installed

    def get_metadata(self):
        """Get a package's metadata, if there is any"""
        if self.full_name == "None":
            return ''
        return get_metadata(self.full_name)

    def get_properties(self, specific_ebuild = None):
        """ Returns properties of specific ebuild.
            If no ebuild specified, get latest ebuild. """
        #dprint("PORTAGELIB: Package:get_properties()")
        if self.full_name == "None":
            return ''
        if specific_ebuild == None:
            ebuild = self.get_default_ebuild()
            if not ebuild:
                dprint("PORTAGELIB; get_properties(): No ebuild found for %s!" % self.full_name)
                #raise Exception(_('No ebuild found.'))
        else:
            #dprint("PORTAGELIB get_properties(): Using specific ebuild")
            ebuild = specific_ebuild
        if not ebuild in self.properties:
            #dprint("portagelib: geting properties for '%s'" % str(ebuild))
            self.properties[ebuild] = get_properties(ebuild)
        return self.properties[ebuild]

    def get_versions(self, include_masked = True):
        """Returns all available ebuilds for the package"""
        if self.full_name == "None":
            return ''
        # Note: this is slow, especially when include_masked is false
        criterion = include_masked and 'match-all' or 'match-visible'
        #dprint("PORTAGELIb: get_versions(); criterion = %s, package = %s" %(str(criterion),self.full_name))
        v = portage.portdb.xmatch(criterion, str(self.full_name))
        dprint("PORTAGELIb: Package.get_versions(); v = %s" %str(v))
        return  v #portage.portdb.xmatch(criterion, str(self.full_name))

    def get_hard_masked(self, check_unmask = False):
        """Returns all versions hard masked by package.mask.
        if check_unmask is True, it excludes packages in package.unmask"""
        if self.full_name == "None":
            return ''
        if self.hard_masked_nocheck == None:
            hardmasked = []
            try:
                for x in portage.portdb.mysettings.pmaskdict[str(self.full_name)]:
                    m = portage.portdb.xmatch("match-all",x)
                    for n in m:
                        if n not in hardmasked: hardmasked.append(n)
            except KeyError:
                pass
            self.hard_masked_nocheck = hardmasked[:]
            try:
                for x in portage.portdb.mysettings.punmaskdict[str(self.full_name)]:
                    m = portage.portdb.xmatch("match-all",x)
                    for n in m:
                        while n in hardmasked: hardmasked.remove(n)
            except KeyError:
                pass
            self.hard_masked = hardmasked
        if check_unmask: return self.hard_masked
        else: return self.hard_masked_nocheck
        

    def is_upgradable(self):
        """Indicates whether an unmasked upgrade/downgrade is available.
        If portage wants to upgrade the package, returns 1.
        If portage wants to downgrade the package, returns -1.
        Else, returns 0.
        """
        if self.full_name == "None":
            return 0
        if self.upgradable == None:
            best = self.get_best_ebuild()
            installed = self.get_latest_installed()
            if not best or not installed:
                self.upgradable = 0
                return self.upgradable
            better = portage.best([best,installed])
            if best == installed:
                self.upgradable = 0
            elif better == best:
                self.upgradable = 1
            elif better == installed:
                self.upgradable = -1
        return self.upgradable

def sort(list):
    """sort in alphabetic instead of ASCIIbetic order"""
    dprint("PORTAGELIB: sort()")
    spam = [(x[0].upper(), x) for x in list]
    spam.sort()
    dprint("PORTAGELIB: sort(); finished")
    return [x[1] for x in spam]


class Database:
    def __init__(self):
        # category dictionary with sorted lists of packages
        self.categories = {}
        # all packages in a list sorted by package name
        self.list = []
        # category dictionary with sorted lists of installed packages
        self.installed = {}
        # keep track of the number of installed packages
        self.installed_count = 0
        # the next 2 tuples hold pkg counts for each category
        self.pkg_count = {}
        self.installed_pkg_count = {}
        
    def get_package(self, full_name):
        """Get a Package object based on full name."""
        try:
            category = get_category(full_name)
            name = get_name(full_name)
            if (category in self.categories
                and name in self.categories[category]):
                return self.categories[category][name]
            else:
                return None
        except:
            return None

    def update_package(self, fullname):
        """Update the package info in the full list and the installed list"""
        #category, name = fullname.split("/")
        category = get_category(full_name)
        name = get_name(full_name)
        if (category in self.categories and name in self.categories[category]):
            self.categories[category][name].update_info()
        if (category in self.installed and name in self.installed[category]):
            self.installed[category][name].update_info()


class DatabaseReader(threading.Thread):
    """Builds the database in a separate thread."""

    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.setDaemon(1)     # quit even if this thread is still running
        self.db = Database()        # the database
        self.callback = callback
        self.done = False     # false if the thread is still working
        #self.count = 0        # number of packages read so far
        self.nodecount = 0    # number of nodes read so far
        self.error = ""       # may contain error message after completion
        # we aren't done yet
        self.done = False
        # cancelled will be set when the thread should stop
        self.cancelled = False
        #self.new_installed_Semaphore = threading.Semaphore()
        self.installed_list = None
        self.allnodes_length = 0  # used for calculating the progress bar
        self.world = get_world()

    def please_die(self):
        """ Tell the thread to die """
        self.cancelled = True

    def get_db(self):
        """Returns the database that was read."""
        return self.db

    def read_db(self):
        """Read portage's database and store it nicely"""
        global thread_id
        dprint("PORTAGELIB: read_db(); process id = %d, thread_id = %d *****************" %(os.getpid(),thread_id))
        self.get_installed()
        try:
            dprint("PORTAGELIB: read_db(); getting allnodes package list")
            allnodes = portage.db['/']['porttree'].getallnodes()[:] # copy
            dprint("PORTAGELIB: read_db(); Done getting allnodes package list")
        except OSError, e:
            # I once forgot to give read permissions
            # to an ebuild I created in the portage overlay.
            self.error = str(e)
            return
        self.allnodes_length = len(allnodes)
        dprint("PORTAGELIB: read_db() create internal porthole list; length=%d" %self.allnodes_length)
        #dsave("db_allnodes_cache", allnodes)
        dprint("PORTAGELIB: read_db(); Threading info: %s" %str(threading.enumerate()) )
        count = 0
        for entry in allnodes:
            if self.cancelled: self.done = True; return
            if count == 250:  # update the statusbar
                self.nodecount += count
                #dprint("PORTAGELIB: read_db(); count = %d" %count)
                self.callback({"nodecount": self.nodecount, "allnodes_length": self.allnodes_length,
                                "done": self.done})
                count = 0
            #dprint("PORTAGELIB: entry = %s" %entry)
            category, name = entry.split('/')
            if category in ["metadata", "distfiles", "eclass"]:
                continue
            # why does getallnodes() return timestamps?
            if (name.endswith('tbz2') or \
                    name.startswith('.') or \
                    name in ['timestamp.x', 'metadata.xml', 'CVS'] ):
                continue
            count += 1
            data = Package(entry)
            if self.cancelled: self.done = True; return
            #self.db.categories.setdefault(category, {})[name] = data;
            # look out for segfaults
            if category not in self.db.categories:
                self.db.categories[category] = {}
                self.db.pkg_count[category] = 0
                #dprint("added category %s" % str(category))
            self.db.categories[category][name] = data;
            if entry in self.installed_list:
                if category not in self.db.installed:
                    self.db.installed[category] = {}
                    self.db.installed_pkg_count[category] = 0
                    #dprint("added category %s to installed" % str(category))
                self.db.installed[category][name] = data
                self.db.installed_pkg_count[category] += 1
                self.db.installed_count += 1
                #dprint("PORTAGELIB: read_db(); adding %s to db.list" %name)
            self.db.list.append((name, data))
            self.db.pkg_count[category] += 1
        dprint("PKGCORE_LIB: read_db(); end of list build; count = %d nodecount = %d" %(count,self.nodecount))
        self.nodecount += count
        dprint("PKGCORE_LIB: read_db(); end of list build; final nodecount = %d categories = %d sort is next" \
                %(self.nodecount, len(self.db.categories)))
        #dprint(self.db)
        self.db.list = self.sort(self.db.list)
        #dprint(self.db)
        dprint("PORTAGELIB: read_db(); end of sort, finished")

    def get_installed(self):
        """get a new installed list"""
        # I believe this next variable may be the cause of our segfaults
        # so I' am semaphoring it.  Brian 2004/08/19
        #self.new_installed_Semaphore.acquire()
        #installed_list # a better way to do this?
        dprint("PORTAGELIB: get_installed();")
        self.installed_list = portage.db['/']['vartree'].getallnodes()[:] # try copying...
        global Installed_Semaphore
        global installed
        Installed_Semaphore.acquire()
        installed = self.installed_list
        Installed_Semaphore.release()
        #self.new_installed_Semaphore.release()
        
    def run(self):
        """The thread function."""
        self.read_db()
        self.done = True   # tell main thread that this thread has finished and pass back the db
        self.callback({"nodecount": self.nodecount, "done": True})
        dprint("PORTAGELIB: DatabaseReader.run(); finished")

    def sort(self, list):
        """sort in alphabetic instead of ASCIIbetic order"""
        dprint("PORTAGELIB: DatabaseReader.sort()")
        spam = [(x[0].upper(), x) for x in list]
        spam.sort()
        dprint("PORTAGELIB: sort(); finished")
        return [x[1] for x in spam]



if __name__ == "__main__":
    def main():
        # test program
        debug = True
##         print (read_access() and "Read access" or "No read access")
##         print (write_access() and "Write access" or "No write access")
        import time, sys
        db_thread = DatabaseReader(); db_thread.run(); db_thread.done = True
        while not db_thread.done:
            print >>sys.stderr, db_thread.count,
            time.sleep(0.1)
        print
        db = db_thread.get_db()
        return
        while 1:
            print; print "Enter full package name:"
            queries = sys.stdin.readline().split()
            for query in queries:
                print; print query
                package = db.get_package(query)
                if not package:
                    print "--- unknown ---"
                    continue
                props = package.get_properties()
                print "Homepages:", props.get_homepages()
                print "Description:", props.description
                print "License:", props.license
                print "Slot:", props.get_slot()
                print "Keywords:", props.get_keywords()
                print "USE flags:", props.get_use_flags()
                print "Installed:", package.get_installed()
                print "Latest:", get_version(package.get_latest_ebuild())
                print ("Latest unmasked:",
                       get_version(package.get_latest_ebuild(0)))

##    main()
    import profile, pstats
    profile.run("main()", "stats.txt")

    stats = pstats.Stats("stats.txt")
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    #stats.sort_stats('time')
    #stats.sort_stats('calls')
    stats.print_stats(0.2)
