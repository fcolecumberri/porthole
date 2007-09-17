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
import utils.debug
from utils.utils import  is_root
from utils.dispatcher import Dispatcher
from sterminal import SimpleTerminal
from sys import exit, stderr
import os
from gettext import gettext as _
import version_sort
from properties import Properties
import config

try:
    import portage
    import portage_const
    import portage_manifest
    print >>stderr, ("PORTAGELIB: portage version = " + portage.VERSION)
except ImportError:
    exit(_('Could not find portage module.\n'
         'Are you sure this is a Gentoo system?'))
         

import threading

from metadata import parse_metadata
from utils.utils import is_root

thread_id = os.getpid()



if is_root(): # then import some modules and run it directly
    import set_config

def get_user_config(file, name=None, ebuild=None):
    """ depricated function. this is now part of the db.user_configs module
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
    utils.debug.dprint("PORTAGELIB: DEPRICATED FUNCTION! get_user_config('%s'), PLEASE update the code calling this function to use db.userconfigs.get_user_config()" % file)
    maskfiles = ['package.mask', 'package.unmask']
    otherfiles = ['package.use', 'package.keywords']
    package_files = otherfiles + maskfiles
    if file not in package_files:
        utils.debug.dprint(" * PORTAGELIB: get_user_config(): unsupported config file '%s'" % file)
        return None
    filename = '/'.join([portage_const.USER_CONFIG_PATH, file])
    if not os.access(filename, os.R_OK):
        utils.debug.dprint(" * PORTAGELIB: get_user_config(): no read access on '%s'?" % file)
        return {}
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

def set_user_config( file, name='', ebuild='', add='', remove='', callback=None):
    """depricated function. this is now part of the db.user_configs module
    Function for parsing package.use, package.mask, package.unmask
    and package.keywords.

    Adds <name> or '=' + <ebuild> to <file> with flags <add>.
    If an existing entry is found, items in <remove> are removed and <add> is added.
    
    If <name> and <ebuild> are not given then lines starting with something in
    remove are removed, and items in <add> are added as new lines.
    """
    utils.debug.dprint("PORTAGELIB: DEPRICATED FUNCTION! set_user_config(); depricated update calling code to use the db.user_configs module")
    command = ''
    maskfiles = ['package.mask', 'package.unmask']
    otherfiles = ['package.use', 'package.keywords']
    package_files = otherfiles + maskfiles
    if file not in package_files:
        utils.debug.dprint(" * PORTAGELIB: set_user_config(); unsupported config file '%s'" % file)
        return False
    if isinstance(add, list):
        add = ' '.join(add)
    if isinstance(remove, list):
        remove = ' '.join(remove)
    config_path = portage_const.USER_CONFIG_PATH
    if not os.access(config_path, os.W_OK):
        commandlist = [config.Prefs.globals.su, '"python', config.Prefs.DATA_PATH + 'backends/set_config.py -d -f %s' %file]
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
        utils.debug.dprint(" * PORTAGELIB: set_user_config(); command = %s" %command )
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

def get_make_conf(want_linelist=False, savecopy=False):
    """
    Parses /etc/make.conf into a dictionary of items with
    dict[setting] = properties string
    
    If want_linelist is True, the list of lines read from make.conf will also
    be returned.
    
    If savecopy is true, a copy of make.conf is saved in make.conf.bak.
    """
    utils.debug.dprint("PORTAGELIB: get_make_conf()")
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
                utils.debug.dprint(" * PORTAGELIB: get_make_conf(): couldn't handle line '%s'. Ignoring" % line)
                linelist.append([strippedline])
            else:
                linelist.append(splitline)
            #linelist.append([splitline[0]])
            #linelist[-1].append('='.join(splitline[1:])) # might have been another '='
        else:
            utils.debug.dprint(" * PORTAGELIB: get_make_conf(): couldn't handle line '%s'. Ignoring" % line)
            linelist.append([strippedline])
    dict = {}
    for line in linelist:
        if len(line) == 2:
            dict[line[0]] = line[1].strip('"') # line[1] should be of form '"settings"'
    if want_linelist:
        return dict, linelist
    return dict

def set_make_conf(property, add='', remove='', replace='', callback=None):
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
    utils.debug.dprint("PORTAGELIB: set_make_conf()")
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
        command = (config.Prefs.globals.su + ' "python ' + config.Prefs.DATA_PATH + 'backends/set_config.py -d -f %s ' %file)
        command = (command + '-p %s ' % property)
        if add != '':
            command = (command + '-a %s ' %("'" + add + "'"))
        if remove != '':
            command = (command + '-r %s' %("'" + remove + "'"))
        command = command + '"'
        utils.debug.dprint(" * PORTAGELIB: set_make_conf(); command = %s" %command )
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

def get_virtuals():
    return portage.settings.virtuals
    
def reload_portage():
    utils.debug.dprint('PORTAGELIB: reloading portage')
    utils.debug.dprint("PORTAGELIB: old portage version = " + portage.VERSION)
    reload(portage)
    utils.debug.dprint("PORTAGELIB: new portage version = " + portage.VERSION)


def get_world():
        world = []
        try:
            file = open("/var/lib/portage/world", "r")
            world = file.read().split()
            file.close()
        except:
            utils.debug.dprint("PORTAGELIB: get_world(); Failure to locate file: '/var/lib/portage/world'")
            utils.debug.dprint("PORTAGELIB: get_world(); Trying '/var/cache/edb/world'")
            try:
                file = open("/var/cache/edb/world", "r")
                world = file.read().split()
                file.close()
                utils.debug.dprint("PORTAGELIB: get_world(); OK")
            except:
                utils.debug.dprint("PORTAGELIB: get_world(); Failed to locate the world file")
        return world

def get_sets_list( filename ):
    """Get the package list file and turn it into a tuple
       attributes: pkgs[key = full_name] = [atoms, version]"""
    pkgs = {}
    try:
        list = read_bash(filename)
    except:
        utils.debug.dprint("PORTAGELIB: get_sets_list(); Failure to locate file: %s" %filename)
        return None
    # split the atoms from the pkg name and any trailing attributes if any
    for item in list:
        parts = split_atom_pkg(item)
        pkgs[parts[0]] = parts[1:]
    return pkgs

def split_atom_pkg( pkg ):
    """Extract [category/package, atoms, version] from some ebuild identifier"""
    #utils.debug.dprint("PORTAGELIB: split_atom_pkg(); pkg = " +pkg)
    atoms = []
    version = ''
    ver_suffix = ''
    if pkg.endswith("*"):
        pkg = pkg[:-1]
        ver_suffix = '*'
    while pkg[0] in ["<",">","=","!","*"]:
        #utils.debug.dprint("PORTAGELIB: split_atom_pkg(); pkg = " + str(pkg))
        atoms.append(pkg[0])
        pkg = pkg[1:]
    cplist = portage.catpkgsplit(pkg) or portage.catsplit(pkg)
    #utils.debug.dprint("PORTAGELIB: split_atom_pkg(); cplist = " + str(cplist))
    if not cplist or len(cplist) < 2:
        utils.debug.dprint("PORTAGELIB split_atom_pkg(): issues with '%s'" % pkg)
        return ['', '', '']
    cp = cplist[0] + "/" + cplist[1]
    #utils.debug.dprint("PORTAGELIB: split_atom_pkg(); cplist2 = " + str(cplist))
    if cplist:
        if len(cplist) >2:
            version = cplist[2] + ver_suffix
        if len(cplist) >3 and cplist[3] != 'r0':
            version += '-' + cplist[3]
    return [str(cp), ''.join(atoms), version] # hmm ... unicode keeps appearing :(


def reload_world():
    utils.debug.dprint("PORTAGELIB: reset_world();")
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
        try: # got an error starting porthole==> added code to catch it, but it works again???
            dict[data[1].strip()] = ['local', data[0].strip(), item[index+3:]]
        except:
            utils.debug.dprint("PORTAGELIB: get_use_flag_dict(); error in index??? data[0].strip, item[index:]")
            utils.debug.dprint(data[0].strip())
            utils.debug.dprint(item[index:])
    return dict

    
def get_portage_environ(var):
    """Returns environment variable from portage if possible, else None"""
    try: temp = portage.config(clone=portage.settings).environ()[var]
    except: temp = None
    return temp

def get_arch():
    """Return host CPU architecture"""
    return portage.settings["ARCH"]

def get_name(full_name):
    """Extract name from full name."""
    return full_name.split('/')[1]

def pkgsplit(ebuild):
    """Split ebuild into [category/package, version, revision]"""
    utils.debug.dprint("PORTAGELIB: pkgsplit(); calling portage function")
    return portage.pkgsplit(ebuild)

def get_category(full_name):
    """Extract category from full name."""
    return full_name.split('/')[0]

def get_full_name(ebuild):
    """Extract category/package from some ebuild identifier"""
    return split_atom_pkg(ebuild)[0]
    # portage.catpkgsplit now pukes when it gets atoms
    ## depricated
    ##if ebuild.endswith("*"): ebuild = ebuild[:-1]
    ##cplist = portage.catpkgsplit(ebuild) or portage.catsplit(ebuild)
    ##if not cplist or len(cplist) < 2:
    ##    utils.debug.dprint("PORTAGELIB get_full_name(): issues with '%s'" % ebuild)
    ##    return ''
    ##cp = cplist[0] + "/" + cplist[1]
    ##while cp[0] in ["<",">","=","!","*","~"]: cp = cp[1:]
    ##return str(cp) # hmm ... unicode keeps appearing :(

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
    return portage.portdb.xmatch(*args, **kwargs)[:] # make a copy.  needed for <portage-svn-r5382

def get_version(ebuild):
    """Extract version number from ebuild name"""
    result = ''
    parts = portage.catpkgsplit(ebuild)
    if parts:
        result = parts[2]
        if parts[3] != 'r0':
            result += '-' + parts[3]
    return result

def get_versions(full_name, include_masked = True):
    """Returns all available ebuilds for the package"""
    # Note: this is slow, especially when include_masked is false
    criterion = include_masked and 'match-all' or 'match-visible'
    v = xmatch(criterion, str(full_name))
    #utils.debug.dprint("PORTAGELIB: get_versions(); criterion = %s, package = %s, v = %s" %(str(criterion),full_name,str(v)))
    return  v

def get_hard_masked(full_name):
	full_name = str(full_name)
	hardmasked = []
	try:
		for x in portage.portdb.mysettings.pmaskdict[full_name]:
			m = xmatch("match-all",x)
			for n in m:
				if n not in hardmasked: hardmasked.append(n)
	except KeyError:
		pass
	hard_masked_nocheck = hardmasked[:]
	try:
		for x in portage.portdb.mysettings.punmaskdict[full_name]:
			m = xmatch("match-all",x)
			for n in m:
				while n in hardmasked: hardmasked.remove(n)
	except KeyError:
		pass
	return hard_masked_nocheck, hardmasked


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

def get_best_ebuild(full_name):
	return xmatch("bestmatch-visible",str(full_name)) # no unicode

def get_dep_ebuild(dep):
    """progreesively checks for available ebuilds that match the dependency.
    returns what it finds as up to three options."""
    #utils.debug.dprint("PORTAGELIB: get_dep_ebuild(); dep = " + dep)
    best_ebuild = keyworded_ebuild = masked_ebuild = ''
    best_ebuild = xmatch("bestmatch-visible", dep)
    if best_ebuild == '':
        #utils.debug.dprint("PORTAGELIB: get_dep_ebuild(); checking masked packages")
        full_name = split_atom_pkg(dep)[0]
        hardmasked_nocheck, hardmasked = get_hard_masked(full_name)
        matches = xmatch("match-all", dep)[:]
        masked_ebuild = best(matches)
        for m in matches:
            if m in hardmasked:
                matches.remove(m)
        keyworded_ebuild = best(matches)
    #utils.debug.dprint("PORTAGELIB: get_dep_ebuild(); ebuilds = " + str([best_ebuild, keyworded_ebuild, masked_ebuild]))
    return best_ebuild, keyworded_ebuild, masked_ebuild


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

def get_size(mycpv):
    """ Returns size of package to fetch. """
    #This code to calculate size of downloaded files was taken from /usr/bin/emerge - BB
    # new code chunks from emerge since the files/digest is no longer, info now in Manifest.
    #utils.debug.dprint( "PORTAGELIB: get_size; mycpv = " + mycpv)
    mysum = [0,'']
    myebuild = portdb.findname(mycpv)
    pkgdir = os.path.dirname(myebuild)
    mf = portage_manifest.Manifest(pkgdir, settings["DISTDIR"])
    fetchlist = portdb.getfetchlist(mycpv, mysettings=settings, all=True)[1]
    #utils.debug.dprint( "PORTAGELIB: get_size; fetchlist = " + str(fetchlist))
    try:
        #utils.debug.dprint( "PORTAGELIB: get_size; mf.getDistfilesSize()")
        mysum[0] = mf.getDistfilesSize(fetchlist)
        mystr = str(mysum[0]/1024)
        #utils.debug.dprint( "PORTAGELIB: get_size; mystr = " + mystr)
        mycount=len(mystr)
        while (mycount > 3):
            mycount-=3
            mystr=mystr[:mycount]+","+mystr[mycount:]
        mysum[1]=mystr+" kB"
    except KeyError, e:
        mysum[1] = "Unknown (missing digest)"
        utils.debug.dprint( "PORTAGELIB: get_size; Exception: " + str(e)  )
        utils.debug.dprint( "PORTAGELIB: get_size; ebuild: " + str(mycpv))
    #utils.debug.dprint( "PORTAGELIB: get_size; returning mysum[1] = " + mysum[1])
    return mysum[1]

def get_digest(ebuild): ## depricated
    """Returns digest of an ebuild"""
    mydigest = portage.db['/']['porttree'].dbapi.finddigest(ebuild)
    digest_file = []
    if mydigest != "":
        try:
            myfile = open(mydigest,"r")
            for line in myfile.readlines():
                digest_file.append(line.split(" "))
            myfile.close()
        except SystemExit, e:
            raise # Needed else can't exit
        except Exception, e:
            utils.debug.dprint("PORTAGELIB: get_digest(): Exception: %s" % e)
    return digest_file

def get_properties(ebuild):
    """Get all ebuild variables in one chunk."""
    ebuild = str(ebuild) #just in case
    if portage.portdb.cpv_exists(ebuild): # if in portage tree
        try:
            return Properties(dict(zip(keys, portage.portdb.aux_get(ebuild, portage.auxdbkeys))))
        except IOError, e: # Sync being performed may delete files
            utils.debug.dprint(" * PORTAGELIB: get_properties(): IOError: %s" % e)
            return Properties()
    else:
        vartree = portage.db['/']['vartree']
        if vartree.dbapi.cpv_exists(ebuild): # elif in installed pkg tree
            return Properties(dict(zip(keys, vartree.dbapi.aux_get(ebuild, portage.auxdbkeys))))
        else: return Properties()

def get_virtual_dep(atom):
    """returns a resolved virtual dependency.
    contributed by Jason Stubbs, with a little adaptation"""
    # Thanks Jason
    non_virtual_atom = portage.dep_virtual([atom], portage.settings)[0]
    if atom == non_virtual_atom:
        # atom,"is a 'new style' virtual (aka regular package)"
        return atom
    else:
        # atom,"is an 'old style' virtual that resolves to:  non_virtual_atom
        return non_virtual_atom


def is_overlay(cpv): # lifted from gentoolkit
    """Returns true if the package is in an overlay."""
    try:
        dir,ovl = portage.portdb.findname2(cpv)
    except:
        return False
    return ovl != portdir

def get_overlay(cpv):
    """Returns an overlay."""
    if '/' not in cpv:
        return ''
    try:
        dir,ovl = portage.portdb.findname2(cpv)
    except:
        ovl = 'Depricated?'
    return ovl

def get_path(cpv):
    """Returns a path to the specified category/package-version"""
    if '/' not in cpv:
        return ''
    try:
        dir,ovl = portage.portdb.findname2(cpv)
    except:
        dir = ''
    return dir
    
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
			pkg = find_best_match(cpv[1:])
			if pkg:
				resolved.append(get_full_name(pkg))
			else:
				unresolved.append(get_full_name(cpv))
	return (resolved + unresolved)


def find_best_match(search_key): # lifted from gentoolkit and updated
    """Returns a Package object for the best available installed candidate that
    matched the search key. Doesn't handle virtuals perfectly"""
    # FIXME: How should we handle versioned virtuals??
    #cat,pkg,ver,rev = split_package_name(search_key)
    full_name = split_atom_pkg(search_key)[0]
    if "virtual" == get_category(full_name):
        #t= get_virtual_dep(search_key)
        t = portage.db["/"]["vartree"].dep_bestmatch(full_name)
    else:
        t = portage.db["/"]["vartree"].dep_bestmatch(search_key)
    if t:
        #utils.debug.dprint("PORTAGELIB: find_best_match(search_key)=" + search_key + " ==> " + str(t))
        return t
    utils.debug.dprint("PORTAGELIB: find_best_match(search_key)=" + search_key + " None Found")
    return None

def split_package_name(name): # lifted from gentoolkit, handles vituals for find_best_match()
    """Returns a list on the form [category, name, version, revision]. Revision will
    be 'r0' if none can be inferred. Category and version will be empty, if none can
    be inferred."""
    utils.debug.dprint(" * PORTAGELIB: split_package_name() name = " + name)
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

def get_allnodes():
    return portage.db['/']['porttree'].getallnodes()[:] # copy
        
def get_installed_list():
    return portage.db['/']['vartree'].getallnodes()[:] # try copying...

def get_installed_ebuild_path(fullname):
    return portage.db['/']['vartree'].getebuildpath(fullname)

def reset_use_flags():
    utils.debug.dprint("PORTAGELIB: reset_use_flags();")
    global SystemUseFlags
    SystemUseFlags = get_portage_environ("USE").split()

def load_emerge_config(trees=None):
    # Taken from /usr/bin/emerge portage-2.1.2.2  ...Brian
    kwargs = {}
    for k, envvar in (("config_root", "PORTAGE_CONFIGROOT"), ("target_root", "ROOT")):
        kwargs[k] = os.environ.get(envvar, None)
    trees = portage.create_trees(trees=trees, **kwargs)
    
    settings = trees["/"]["vartree"].settings
    
    for myroot in trees:
        if myroot != "/":
            settings = trees[myroot]["vartree"].settings
            break
    
    mtimedbfile = os.path.join("/", portage.CACHE_PATH.lstrip(os.path.sep), "mtimedb")
    mtimedb = portage.MtimeDB(mtimedbfile)
    return settings, trees, mtimedb

settings, trees, mtimedb = load_emerge_config()
portdb = trees[settings["ROOT"]]["porttree"].dbapi

#settings = portage.config(clone=portage.settings)

portdir = portage.config(clone=portage.settings).environ()['PORTDIR']
# is PORTDIR_OVERLAY always defined?
portdir_overlay = get_portage_environ('PORTDIR_OVERLAY')

ACCEPT_KEYWORDS = get_portage_environ("ACCEPT_KEYWORDS")

user_config_dir = portage_const.USER_CONFIG_PATH

# Run it once for sake of efficiency

World = get_world()

SystemUseFlags = get_portage_environ("USE").split()

virtuals = get_virtuals

# lower case is nicer
keys = [key.lower() for key in portage.auxdbkeys]

# Run it once for sake of efficiency
UseFlagDict = get_use_flag_dict()

# debug code follows WFW
#polibkeys = UseFlagDict.keys()
#polibkeys.sort()
#for polibkey in polibkeys:
#    print polibkey, ':', UseFlagDict[polibkey]

