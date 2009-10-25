#!/usr/bin/env python

"""
    PortageLib
    An interface library to Gentoo's Portage

    Copyright (C) 2003 - 2009 Fredrik Arnerup, Daniel G. Taylor,
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

import datetime
id = datetime.datetime.now().microsecond
print "PORTAGELIB: id initialized to ", id

from sys import exit, stderr
import os, thread
from gettext import gettext as _

from porthole.utils import debug
from porthole.utils.utils import  is_root
from porthole.utils.dispatcher import Dispatcher, Dispatch_wait
from porthole.sterminal import SimpleTerminal
from porthole.backends import version_sort
from porthole.backends.properties import Properties
from porthole import config
from porthole.backends.metadata import parse_metadata

try: # >=portage 2.2 modules
    import portage
    #print "PORTAGELIB: imported portage-2.2"
    import portage.const as portage_const
    #print "PORTAGELIB: imported portage.const module"
    import portage.manifest as manifest
    #print "PORTAGELIB: imported portage-2.2 manifest"
    from _emerge.actions import load_emerge_config as _load_emerge_config
    PORTAGE22 = True
    print "PORTAGELIB: imported portage-2.2 modules"
except: # portage 2.1.x modules
    print "PORTAGELIB: importing portage-2.1 modules"
    try:
        import portage
        import portage_const
        import portage_manifest as manifest
        PORTAGE22 = False
    except ImportError:
        exit(_('Could not find portage module.\n'
             'Are you sure this is a Gentoo system?'))
print >>stderr, ("PORTAGELIB: portage version = " + portage.VERSION)

#thread_id = os.getpid()
thread_id = thread.get_ident()



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
    debug.dprint("PORTAGELIB: DEPRICATED FUNCTION! get_user_config('%s'), PLEASE update the code calling this function to use db.userconfigs.get_user_config()" % file)
    maskfiles = ['package.mask', 'package.unmask']
    otherfiles = ['package.use', 'package.keywords']
    package_files = otherfiles + maskfiles
    if file not in package_files:
        debug.dprint(" * PORTAGELIB: get_user_config(): unsupported config file '%s'" % file)
        return None
    filename = '/'.join([portage_const.USER_CONFIG_PATH, file])
    if not os.access(filename, os.R_OK):
        debug.dprint(" * PORTAGELIB: get_user_config(): no read access on '%s'?" % file)
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
    debug.dprint("PORTAGELIB: DEPRICATED FUNCTION! set_user_config(); depricated update calling code to use the db.user_configs module")
    command = ''
    maskfiles = ['package.mask', 'package.unmask']
    otherfiles = ['package.use', 'package.keywords']
    package_files = otherfiles + maskfiles
    if file not in package_files:
        debug.dprint(" * PORTAGELIB: set_user_config(); unsupported config file '%s'" % file)
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
        debug.dprint(" * PORTAGELIB: set_user_config(); command = %s" %command )
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
    debug.dprint("PORTAGELIB: get_make_conf()")
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
                debug.dprint(" * PORTAGELIB: get_make_conf(): couldn't handle line '%s'. Ignoring" % line)
                linelist.append([strippedline])
            else:
                linelist.append(splitline)
            #linelist.append([splitline[0]])
            #linelist[-1].append('='.join(splitline[1:])) # might have been another '='
        else:
            debug.dprint(" * PORTAGELIB: get_make_conf(): couldn't handle line '%s'. Ignoring" % line)
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
    debug.dprint("PORTAGELIB: set_make_conf()")
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
        debug.dprint(" * PORTAGELIB: set_make_conf(); command = %s" %command )
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
    return settings.settings.virtuals
    
def reload_portage():
    debug.dprint('PORTAGELIB: reloading portage')
    debug.dprint("PORTAGELIB: old portage version = " + portage.VERSION)
    reload(portage)
    debug.dprint("PORTAGELIB: new portage version = " + portage.VERSION)
    settings.reset()

def get_sets_list( filename ):
    """Get the package list file and turn it into a tuple
       attributes: pkgs[key = full_name] = [atoms, version]"""
    pkgs = {}
    try:
        list = read_bash(filename)
    except:
        debug.dprint("PORTAGELIB: get_sets_list(); Failure to locate file: %s" %filename)
        return None
    # split the atoms from the pkg name and any trailing attributes if any
    for item in list:
        parts = split_atom_pkg(item)
        pkgs[parts[0]] = parts[1:]
    return pkgs

def split_atom_pkg( pkg ):
    """Extract [category/package, atoms, version] from some ebuild identifier"""
    #debug.dprint("PORTAGELIB: split_atom_pkg(); pkg = " +pkg)
    atoms = []
    version = ''
    ver_suffix = ''
    if pkg.endswith("*"):
        pkg = pkg[:-1]
        ver_suffix = '*'
    while pkg[0] in ["<",">","=","!","*"]:
        #debug.dprint("PORTAGELIB: split_atom_pkg(); pkg = " + str(pkg))
        atoms.append(pkg[0])
        pkg = pkg[1:]
    cplist = portage.catpkgsplit(pkg) or portage.catsplit(pkg)
    #debug.dprint("PORTAGELIB: split_atom_pkg(); cplist = " + str(cplist))
    if not cplist or len(cplist) < 2:
        debug.dprint("PORTAGELIB split_atom_pkg(): issues with '%s'" % pkg)
        return ['', '', '']
    cp = cplist[0] + "/" + cplist[1]
    #debug.dprint("PORTAGELIB: split_atom_pkg(); cplist2 = " + str(cplist))
    if cplist:
        if len(cplist) >2:
            version = cplist[2] + ver_suffix
        if len(cplist) >3 and cplist[3] != 'r0':
            version += '-' + cplist[3]
    return [str(cp), ''.join(atoms), version] # hmm ... unicode keeps appearing :(

def get_use_flag_dict(portdir):
    """ Get all the use flags and return them as a dictionary 
        key = use flag forced to lowercase
        data = list[0] = 'local' or 'global'
               list[1] = 'package-name'
               list[2] = description of flag   
    """
    dict = {}

    # process standard use flags

    List = portage.grabfile(portdir + '/profiles/use.desc')
    for item in List:
        index = item.find(' - ')
        dict[item[:index].strip().lower()] = ['global', '', item[index+3:]]

    # process local (package specific) use flags

    List = portage.grabfile(portdir + '/profiles/use.local.desc')
    for item in List:
        index = item.find(' - ')
        data = item[:index].lower().split(':')
        try: # got an error starting porthole==> added code to catch it, but it works again???
            dict[data[1].strip()] = ['local', data[0].strip(), item[index+3:]]
        except:
            debug.dprint("PORTAGELIB: get_use_flag_dict(); error in index??? data[0].strip, item[index:]")
            debug.dprint(data[0].strip())
            debug.dprint(item[index:])
    return dict
    
def get_portage_environ(var):
    """Returns environment variable from portage if possible, else None"""
    try: 
        #temp = portage.config(clone=portage.settings).environ()[var]
        temp = settings.settings.environ()[var]
    except: temp = None
    return temp

def get_arch():
    """Return host CPU architecture"""
    return settings.settings["ARCH"]

def get_cpv_use(cpv):
    """uses portage to determine final USE flags and settings for an emerge"""
    debug.dprint("PORTAGELIB: get_cpv_use(); cpv = " + cpv)
    myuse = None
    settings.settings.unlock()
    settings.settings.setcpv(cpv, use_cache=True, mydb=settings.portdb)
    myuse = settings.settings['PORTAGE_USE'].split()
    debug.dprint("PORTAGELIB: get_cpv_use(); type(myuse), myuse = " + str(type(myuse)) + str(myuse))
    #use_expand_hidden =  settings.settings._get_implicit_iuse()
    use_expand_hidden = settings.settings["USE_EXPAND_HIDDEN"].split()
    debug.dprint("PORTAGELIB: get_cpv_use(); type(use_expand_hidden), use_expand_hidden = " + str(type(use_expand_hidden)) + str(use_expand_hidden))
    usemask = list(settings.settings.usemask)
    useforce =  list(settings.settings.useforce)
    # reset cpv filter
    settings.settings.reset()
    settings.settings.lock()
    return myuse, use_expand_hidden, usemask, useforce

def get_name(full_name):
    """Extract name from full name."""
    return full_name.split('/')[1]

def pkgsplit(ebuild):
    """Split ebuild into [category/package, version, revision]"""
    debug.dprint("PORTAGELIB: pkgsplit(); calling portage function")
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
    ##    debug.dprint("PORTAGELIB get_full_name(): issues with '%s'" % ebuild)
    ##    return ''
    ##cp = cplist[0] + "/" + cplist[1]
    ##while cp[0] in ["<",">","=","!","*","~"]: cp = cp[1:]
    ##return str(cp) # hmm ... unicode keeps appearing :(

def get_installed(package_name):
    """Extract installed versions from package_name.
    package_name can be the short package name ('eric'), long package name ('dev-util/eric')
    or a version-matching string ('>=dev-util/eric-2.5.1:2[flag1 flag2]')
    """
    return settings.trees[settings.settings["ROOT"]]["vartree"].dep_match(str(package_name))

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
    #print >>stderr, "PORTAGELIB: xmatch(); thread ident ", thread.get_ident()
    results  =  settings.portdb.xmatch(*args, **kwargs)[:] # make a copy.  needed for <portage-svn-r5382
    #print >>stderr, type(results), str(results)
    return results

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
    #debug.dprint("PORTAGELIB: get_versions(); criterion = %s, package = %s, v = %s" %(str(criterion),full_name,str(v)))
    return  v

def get_hard_masked(full_name):
    full_name = str(full_name)
    hardmasked = []
    try:
        for x in settings.portdb.mysettings.pmaskdict[full_name]:
            m = xmatch("match-all",x)
            for n in m:
                if n not in hardmasked: hardmasked.append(n)
    except KeyError:
        pass
    hard_masked_nocheck = hardmasked[:]
    try:
        for x in settings.portdb.mysettings.punmaskdict[full_name]:
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
    if settings.portdb.cpv_exists(ebuild): # if in portage tree
        return settings.portdb.aux_get(ebuild, [property])[0]
    else:
        vartree = settings.trees[settings.settings["ROOT"]]["vartree"]
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
    #debug.dprint("PORTAGELIB: get_dep_ebuild(); dep = " + dep)
    best_ebuild = keyworded_ebuild = masked_ebuild = ''
    best_ebuild = xmatch("bestmatch-visible", dep)
    if best_ebuild == '':
        #debug.dprint("PORTAGELIB: get_dep_ebuild(); checking masked packages")
        full_name = split_atom_pkg(dep)[0]
        hardmasked_nocheck, hardmasked = get_hard_masked(full_name)
        matches = xmatch("match-all", dep)[:]
        masked_ebuild = best(matches)
        for m in matches:
            if m in hardmasked:
                matches.remove(m)
        keyworded_ebuild = best(matches)
    #debug.dprint("PORTAGELIB: get_dep_ebuild(); ebuilds = " + str([best_ebuild, keyworded_ebuild, masked_ebuild]))
    return best_ebuild, keyworded_ebuild, masked_ebuild


def get_archlist():
    """lists the architectures accepted by portage as valid keywords"""
    return settings.settings["PORTAGE_ARCHLIST"].split()
    #~ list = portage.archlist[:]
    #~ for entry in list:
        #~ if entry.startswith("~"):
            #~ list.remove(entry)
    #~ return list

def get_masking_reason(ebuild):
    """Strips trailing \n from, and returns the masking reason given by portage"""
    reason, location = portage.getmaskingreason(ebuild, settings=settings.settings, portdb=settings.portdb,  return_location=True)
    if not reason: return _('No masking reason given')
    if location != None:
        reason += "in file: " + location
    if reason.endswith("\n"):
        reason = reason[:-1]
    return reason

def get_size(mycpv):
    """ Returns size of package to fetch. """
    #This code to calculate size of downloaded files was taken from /usr/bin/emerge - BB
    # new code chunks from emerge since the files/digest is no longer, info now in Manifest.
    #debug.dprint( "PORTAGELIB: get_size; mycpv = " + mycpv)
    mysum = [0,'']
    myebuild = settings.portdb.findname(mycpv)
    pkgdir = os.path.dirname(myebuild)
    mf = manifest.Manifest(pkgdir, settings.settings["DISTDIR"])
    #debug.dprint( "PORTAGELIB: get_size; Attempting to get fetchlist")
    try:
        if portage.VERSION >= '2.1.6':# newer portage
            fetchlist = settings.portdb.getFetchMap(mycpv) 
        else:
            debug.dprint( "PORTAGELIB: get_size; Trying old fetchlist call")
            fetchlist = settings.portdb.getfetchlist(mycpv, mysettings=settings.settings, all=True)[1]
        #debug.dprint( "PORTAGELIB: get_size; mf.getDistfilesSize()")
        mysum[0] = mf.getDistfilesSize(fetchlist)
        mystr = str(mysum[0]/1024)
        #debug.dprint( "PORTAGELIB: get_size; mystr = " + mystr)
        mycount=len(mystr)
        while (mycount > 3):
            mycount-=3
            mystr=mystr[:mycount]+","+mystr[mycount:]
        mysum[1]=mystr+" kB"
    except KeyError, e:
        mysum[1] = "Unknown (missing digest)"
        debug.dprint( "PORTAGELIB: get_size; Exception: " + str(e)  )
        debug.dprint( "PORTAGELIB: get_size; ebuild: " + str(mycpv))
        debug.dprint( "PORTAGELIB: get_size; fetchlist = " + str(fetchlist))
    #debug.dprint( "PORTAGELIB: get_size; returning mysum[1] = " + mysum[1])
    return mysum[1]

def get_digest(ebuild): ## depricated
    """Returns digest of an ebuild"""
    mydigest = settings.portdb.finddigest(ebuild)
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
            debug.dprint("PORTAGELIB: get_digest(): Exception: %s" % e)
    return digest_file

def get_properties(ebuild):
    """Get all ebuild variables in one chunk."""
    ebuild = str(ebuild) #just in case
    if settings.portdb.cpv_exists(ebuild): # if in portage tree
        try:
            return Properties(dict(zip(settings.keys, settings.portdb.aux_get(ebuild, portage.auxdbkeys))))
        except IOError, e: # Sync being performed may delete files
            debug.dprint(" * PORTAGELIB: get_properties(): IOError: %s" % str(e))
            return Properties()
        except Exception, e:
            debug.dprint(" * PORTAGELIB: get_properties(): Exception: %s" %str( e))
            return Properties()
    else:
        vartree = settings.trees[settings.settings["ROOT"]]["vartree"]
        if vartree.dbapi.cpv_exists(ebuild): # elif in installed pkg tree
            return Properties(dict(zip(settings.keys, vartree.dbapi.aux_get(ebuild, portage.auxdbkeys))))
        else: return Properties()

def get_virtual_dep(atom):
    """returns a resolved virtual dependency.
    contributed by Jason Stubbs, with a little adaptation"""
    # Thanks Jason
    non_virtual_atom = portage.dep_virtual([atom], settings.settings)[0]
    if atom == non_virtual_atom:
        # atom,"is a 'new style' virtual (aka regular package)"
        return atom
    else:
        # atom,"is an 'old style' virtual that resolves to:  non_virtual_atom
        return non_virtual_atom


def is_overlay(cpv): # lifted from gentoolkit
    """Returns true if the package is in an overlay."""
    try:
        dir,ovl = settings.portdb.findname2(cpv)
    except:
        return False
    return ovl != settings.portdir

def get_overlay(cpv):
    """Returns an overlay."""
    if '/' not in cpv:
        return ''
    try:
        dir,ovl = settings.portdb.findname2(cpv)
    except:
        ovl = 'Depricated?'
    return ovl

def get_overlay_name(ovl):
    if ovl in settings.repos:
        return settings.repos[ovl]
    return "????"

def get_path(cpv):
    """Returns a path to the specified category/package-version"""
    if '/' not in cpv:
        return ''
    try:
        dir,ovl = settings.portdb.findname2(cpv)
    except:
        dir = ''
    return dir
    
def get_metadata(package):
    """Get the metadata for a package"""
    # we could check the overlay as well,
    # but we are unlikely to find any metadata files there
    try: return parse_metadata(settings.portdir + "/" + package + "/metadata.xml")
    except: return None

def get_system_pkgs(): # lifted from gentoolkit
    """Returns a tuple of lists, first list is resolved system packages,
    second is a list of unresolved packages."""
    pkglist = settings.settings.packages
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
        t = settings.trees[settings.settings["ROOT"]]["vartree"].dep_bestmatch(full_name)
    else:
        t = settings.trees[settings.settings["ROOT"]]["vartree"].dep_bestmatch(search_key)
    if t:
        #debug.dprint("PORTAGELIB: find_best_match(search_key)=" + search_key + " ==> " + str(t))
        return t
    debug.dprint("PORTAGELIB: find_best_match(search_key)=" + search_key + " None Found")
    return None

def split_package_name(name): # lifted from gentoolkit, handles vituals for find_best_match()
    """Returns a list on the form [category, name, version, revision]. Revision will
    be 'r0' if none can be inferred. Category and version will be empty, if none can
    be inferred."""
    debug.dprint(" * PORTAGELIB: split_package_name() name = " + name)
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
    return settings.trees[settings.settings["ROOT"]]['porttree'].getallnodes()[:] # copy
        
def get_installed_list():
    return settings.trees[settings.settings["ROOT"]]["vartree"].getallnodes()[:] # try copying...

def get_installed_ebuild_path(fullname):
    return settings.trees[settings.settings["ROOT"]]["vartree"].getebuildpath(fullname)

class PortageSettings:
    def __init__(self):
        # declare some globals
        self.portdir = self.portdir_overlay = self.ACCEPT_KEYWORDS = self.user_config_dir = self._world = self.SystemUseFlags = None
        self.virtuals = self.keys = self.UseFlagDict = None
        if PORTAGE22: # then use the imported module
            self.my_load_emerge_config = _load_emerge_config
        else: # use the one copied from the non importable emerge
            self.my_load_emerge_config = self.load_emerge_config
        #self.settings, self.trees, self.mtimedb = self.load_emerge_config()
        #self.portdb = self.trees[self.settings["ROOT"]]["porttree"].dbapi
        #self.root_config = self.trees[self.settings["ROOT"]]["root_config"]
        self.reset()

    def reset_use_flags(self):
        debug.dprint("PORTAGELIB: Settings.reset_use_flags();")
        self.SystemUseFlags = portage.settings["USE"].split()
        #debug.dprint("PORTAGELIB: Settings.reset_use_flags(); SystemUseFlags = " + str(SystemUseFlags))

    def load_emerge_config(self, trees = None):
        # Taken from /usr/bin/emerge portage-2.1.2.2  ...Brian  >=portage-2.2* it is import-able
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

    def reset(self):
        """reset remaining run once variables after a sync or other mods"""
        debug.dprint("PORTAGELIB: reset_globals();")
        self.settings, self.trees, self.mtimedb = self.my_load_emerge_config()
        self.portdb = self.trees[self.settings["ROOT"]]["porttree"].dbapi
        #self.db=self.portdb.auxdbmodule._db_module
        #print >>stderr, self.db.__dict__.keys()
        #self.db.dbapi2.check_same_thread  = False
        self.portdir = self.settings.environ()['PORTDIR']
        self.config_root = self.settings['PORTAGE_CONFIGROOT']
        # is PORTDIR_OVERLAY always defined?
        self.portdir_overlay = get_portage_environ('PORTDIR_OVERLAY')
        self.ACCEPT_KEYWORDS = get_portage_environ("ACCEPT_KEYWORDS")
        self.user_config_dir = portage_const.USER_CONFIG_PATH
        self.reload_world()
        self.reset_use_flags()
        self.virtuals = self.settings.virtuals
        # lower case is nicer
        self.keys = [key.lower() for key in portage.auxdbkeys]
        self.UseFlagDict = get_use_flag_dict(self.portdir)
        self.create_repos()
        return

    def create_repos(self):
        # reverse the treemap's key:data for easy name lookup
        t = self.portdb.treemap
        n = {}
        for x in t.keys():
            n[t[x]] = x
        self.repos = n


    def reload_config(self):
        """Reload the whole config from scratch"""
        self.settings, self.trees, self.mtimedb = self.my_load_emerge_config(self.trees)
        self.portdb = self.trees[self.settings["ROOT"]]["porttree"].dbapi
        self.create_repos()

    def reload_world(self):
        debug.dprint("PORTAGELIB: reset_world();")
        world = []
        try:
            file = open(os.path.join('/', portage.WORLD_FILE), "r") #"/var/lib/portage/world", "r")
            world = file.read().split()
            file.close()
        except:
            debug.dprint("PORTAGELIB: get_world(); Failure to locate file: '%s'" %portage.WORLD_FILE)
            debug.dprint("PORTAGELIB: get_world(); Trying '/var/cache/edb/world'")
            try:
                file = open("/var/cache/edb/world", "r")
                world = file.read().split()
                file.close()
                debug.dprint("PORTAGELIB: get_world(); OK")
            except:
                debug.dprint("PORTAGELIB: get_world(); Failed to locate the world file")
        self._world = world

    def get_world(self):
        return self._world

settings = PortageSettings()

func = {'get_virtuals': get_virtuals,
        'split_atom_pkg': split_atom_pkg,
        'get_portage_environ': get_portage_environ,
        'get_installed': get_installed,
        'xmatch': xmatch,
        'get_versions': get_versions,
        'get_hard_masked': get_hard_masked,
        'get_property': get_property,
        'get_best_ebuild': get_best_ebuild,
        'get_dep_ebuild': get_dep_ebuild,
        'get_best_ebuild': get_best_ebuild,
        'get_dep_ebuild': get_dep_ebuild,
        'get_size': get_size,
        'get_properties': get_properties,
        'get_virtual_dep': get_virtual_dep,
        'get_path': get_path,
        'get_system_pkgs': get_system_pkgs,
        'find_best_match': find_best_match,
        'get_installed_list':  get_installed_list
}


def call_waiting(*args, **kwargs):
    """function to handle function calls from other
        threads in this thread and retun results
        
        Parameters: args = [function-name, parameter1,parameter2,...]
        
        """

    call = func[ args[0]]
    arg = args[1:]
    reply = call(*arg)
    return reply

# create our thread call dispatcher
dispatch_wait = Dispatch_wait(call_waiting)



## debug code follows WFW
##polibkeys = UseFlagDict.keys()
##polibkeys.sort()
##for polibkey in polibkeys:
##    print polibkey, ':', UseFlagDict[polibkey]

