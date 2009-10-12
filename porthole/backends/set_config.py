#!/usr/bin/env python

"""
    Set_config
    A config file saving module for porthole

    Copyright (C) 2005 - 2008 Brian Dolbec, Tommy Iorns,
                            Gunnar Wrobel <wrobel@gentoo.org>

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

import sys, os, os.path, codecs, re, datetime

try: # >=portage 2.2 modules
    import portage.const as portage_const
except: # portage 2.1.x modules
    try:
        #import portage
        import portage_const
    except ImportError:
        sys.exit(_('Could not find portage module.\n'
             'Are you sure this is a Gentoo system?'))

#debug = False
debug = True
version = 1.1

def dprint(message):
    """Print debug message if debug is true."""
    if debug:
        print message

def Header(filename):
    """creates a file creation header including:
        # filename
        # name of this program filename
        # program version
        # date & time of creation
        # login username"""
    
    header = "#########################################################################\n" + \
            ("# $Header: %s created by Porthole's set_config.py v: %s, %s, %s Exp $\n" \
            %(filename, str(version), datetime.datetime.today().strftime("%Y/%m/%d %H:%M:%S"), os.getlogin()))
    dprint("SET_CONFIG: Header(); new header:\n%s" % header)
    dprint("SET_CONFIG: Header(); end header:")
    return header


def get_configlines(filename):
    """gets the contents of the input filename if it exists and returns the lines as a list.
        if the file did not exist then it initializes the list with a creation header"""
    if os.access(filename, os.F_OK): # if file exists
        dprint("SET_CONFIG:  get_configlines(); filename -- os.access OK:%s" % filename)
        configfile = open(filename, 'r')
        configlines = configfile.readlines()
        configfile.close()
    else:
        dprint("SET_CONFIG:  get_configlines(); new file: %s" % filename)
        configlines = Header(filename).split('\n')
    return configlines

def chk_permission(filename):
    """checks for write permission on input filename"""
    if not os.access(os.path.split(filename)[0], os.W_OK):
        dprint(" * SET_CONFIG: set_user_config(): no write access to '%s'. " \
              "Perhaps the user is not root?" % os.path.split(filename)[0])
        return False
    return True

def group_by_blanklines(configlines):
    """group lines by separation blank lines to keep entries and their comments together
        input: list of text lines
        returns a tuple of lists""" 
    x=0
    groups={}
    groups[x]=[]
    for s in configlines:
        groups[x].append(s)
        if s == '\n':
            x += 1
            groups[x]=[]
    return groups

def rm_dbl_nl(a):
    """removes multiple consecutive null string list entries and returns a cleaned list
            @a = input list"""
    dprint("SET_CONFIG: rm_dbl_nl(); a= %s" %str(a))
    r=[]
    for x in range(len(a)-1):
        if a[x] == '' and a[x+1] == '':
            continue
        r.append(a[x])
    r.append(a[x+1])
    dprint("SET_CONFIG: rm_dbl_nl(); returning r= %s" %str(r))
    return r

def remove_flag(flag, line):
    # just in case there are multiple entries for the same flag
    if not line:
        return line
    while flag in line:
        line.remove(flag)
        dprint("SET_CONFIG: remove_flag(); removed '%s' from line" % flag)
    return line

def set_user_config(filename, name='', ebuild='', comment = '', add=[], remove=[], delete=[]):
    """
    Adds <name> or '=' + <ebuild> to <filename> with flags <add>.
    If an existing entry is found, items in <remove> are removed and <add> is added.
    
    If <name> and <ebuild> are not given then lines starting with something in
    remove are removed, and items in <add> are added as new lines.
    """
    dprint("SET_CONFIG: set_user_config(): filename = '%s'" % filename)
    if not chk_permission(filename):
        return False
    dprint(" * SET_CONFIG: set_user_config(): filename = " + filename)
    configlines = get_configlines(filename)
    config = [line.split() for line in configlines]
    if not name:
        name =  ebuild
    done = False
    # Check if there is already a line to append to
    for line in config:
        if not line: continue
        #dprint("SET_CONFIG: checking line: "  + str(line) )
        if line[0] == name and line[0] not in remove:
            done = True
            dprint("SET_CONFIG: found line for '%s'" % name)
            for flag in remove:
                line = remove_flag(flag, line)
            for flag in add:
                if flag.startswith('+'):
                    dprint("SET_CONFIG: FIXME! removed leading '+' from %s flag" % flag)
                    flag = flag[1:]
                # check for and remove existing occurance(s) of flag
                line = remove_flag(flag, line)
                if flag not in line:
                    line.append(flag)
                    dprint("SET_CONFIG: added '%s' to line" % flag)
                elif '+' + flag in line:
                    dprint("SET_CONFIG: removing existing '+' from '%s' flag" % flag)
                    line = remove_flag('+' + flag, line)
                    line.append(flag)
                    dprint("SET_CONFIG: added '%s' flag" % flag)
                
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
                return set_user_config(filename, name=cp, remove=remove)
        else: # package.mask/unmask: list of names to add
            config.extend([[item] for item in add])
            dprint("SET_CONFIG: added %d lines to %s" % (len(add), file))
        done = True
    # add one blank line to end (so we end with a \n)
    config.append([''])
    configlines = [' '.join(line) for line in config]
    configlines = rm_dbl_nl(configlines)
    configtext = '\n'.join(configlines)
    configfile = open(filename, 'w')
    configfile.write(configtext)
    configfile.close()
    return True

def set_package_mask(filename, name='', ebuild='', comment='', add=[], remove=[]):
    """routine to handle adding/removing entries in package.mask files which should have multple lines to add/delete"""
    dprint("SET_CONFIG:  set_package_mask(): filename = '%s'" % filename)
    if not chk_permission(filename):
        return False
    #dprint(" * SET_CONFIG: set_package_mask(): filename = " + filename)
    configlines =  get_configlines(filename)
    groups = group_by_blanklines(configlines)
    
    # do some more stuff
    
    configtext = '\n'.join(configlines)
    configfile = open(filename, 'w')
    configfile.write(configtext)
    configfile.close()
    return True

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
    if not os.access(portage_const.MAKE_CONF_FILE, os.W_OK):
        dprint(" * SET_CONFIG: set_make_conf(): no write access to '%s'. " \
              "Perhaps the user is not root?" % portage_const.MAKE_CONF_FILE)
        return False
    makefile = MakeConf(portage_const.MAKE_CONF_FILE)
    values = makefile.read_property(property)
    if remove:
        for element in remove:
            while element in values:
                values.remove(element)
                dprint("SET_CONFIG: removed '%s' from %s" % (element, property))
    if add:
        if not property in makefile.properties:
            dprint("SET_CONFIG: set_make_conf(): makefile does not have key '%s'. Creating..." % property)
            makefile.add_string_property(property, "")
        for element in add:
            if element not in values:
                values.append(element)
                dprint("SET_CONFIG: added '%s' to %s" % (element, property))
        values.sort()
    if replace:
        values = [replace]
        dprint("SET_CONFIG: setting %s to '%s'" % (property, replace))
    # Now write to make.conf, keeping comments, unparsed lines and line order intact
    if not makefile.backup_file(): # just saves a copy with ".bak" on the end
        return False
    return makefile.write_property(property, values)


class MakeConf:
    """Make_config
    A /etc/make.conf file parsing, modifying, saving class module for porthole

    Copyright (C) 2005 - 2008 Brian Dolbec,
        Gunnar Wrobel <wrobel@gentoo.org>

    Much of the following code is derived from code used in layman
        # Author(s): Gunnar Wrobel <wrobel@gentoo.org>
    And then modified and extended for porthole's use by Brian Dolbec
    """
    # define some re's
    regex = {'USE': re.compile('USE\s*=\s*"([^"]*)"'),
                    'PORTDIR_OVERLAY': re.compile('PORTDIR_OVERLAY\s*=\s*"([^"]*)"'),
                    'PORTAGE_NICENESS': re.compile('PORTAGE_NICENESS\s*=\s*([0-9]*)\s*\n')
    }

    def __init__(self, path, config = None, overlays = None):

        self.path = path
        self.config = config
        if self.config:
            self.storage = config['storage']
        else:
            self.storage = ''
        self.data = ''
        self.db = overlays
        self.overlays = []
        self.extra = []
        self.properties = []

    def create_re(self, property):
        """creates the property reg expression and saves it to 
        the regex dictionary for use"""
        if not property in self.regex:
            self.regex[property] = re.compile(('%s\s*=\s*"([^"]*)"') %property)

    def add_overlay(self, overlay):
        '''Add an overlay to make.conf.'''
        self.overlays.append(overlay)
        self.write_overlay()

    def delete_overlay(self, overlay):
        '''Delete an overlay from make.conf.'''
        self.overlays = [i
                         for i in self.overlays
                         if i.name != overlay.name]
        self.write_overlay()

    def read_overlay(self):
        '''Read the list of registered overlays from /etc/make.conf.'''
        if self.data == '':
            self.content()
        if self.data > '':
            overlays = self.regex['PORTDIR_OVERLAY'].search(self.data)
            if not overlays:
                raise Exception('MAKE_CONF: read_overlay(); Did not find a PORTDIR_OVERLAY entry in file ' +
                                self.path +'! Did you specify the correct file?')
            overlays = [i.strip()
                        for i in overlays.group(1).split('\n')
                        if i.strip()]

            if self.db == None: # we do not have the layman db
                return overlays
            for i in overlays:
                if i[:len(self.storage)] == self.storage:
                    oname = os.path.basename(i)
                    if  oname in self.db.keys():
                        self.overlays.append(self.db[oname])
                    else:
                        # These are additional overlays that we dont know
                        # anything about. The user probably added them manually
                        self.extra.append(i)
                else:
                    # These are additional overlays that we dont know anything
                    # about. The user probably added them manually
                    self.extra.append(i)
        return self.overlays + self.extra

    def read_property(self, property):
        '''Read the list of USE flags from /etc/make.conf.'''
        if self.data == '':
            self.content()
        if property not in self.regex:
            self.create_re(property)
        if self.data > '':
            mylist = self.regex[property].search(self.data)
            if not mylist:
                raise Exception('MAKE_CONF: read_property(); Did not find a ' + property + ' entry in file ' +
                                self.path +'! Did you specify the correct file?')
            values = [i.strip()
                        for i in mylist.group(1).split()
                        if i.strip()]
            while '\\' in values:
                values.remove('\\')
        else:
            values = []
            self.data = property + '=""\n'
        #dprint("SET_CONFIG: MakeConf read_property \n%s %s = %s" % (property, len(values), values))
        return values

    def write_overlay(self):
        '''  Write the list of registered overlays to /etc/make.conf.'''
        def prio_sort(a, b):
            '''Sort by priority.'''
            if a.priority < b.priority:
                return -1
            elif a.priority > b.priority:
                return 1
            return 0

        self.overlays.sort(prio_sort)

        paths = []
        for i in self.overlays:
            paths.append(path((self.storage, i.name, )))
        overlays = 'PORTDIR_OVERLAY="\n'
        overlays += '\n'.join(paths) + '\n'
        overlays += '$PORTDIR_OVERLAY\n'
        overlays += '\n'.join(self.extra)
        overlays += '"'
        content = self.OVERLAY_re.sub(overlays, self.data)
        if not self.OVERLAY_re.search(content):
            raise Exception('MAKE_CONF: write_overlay(); failed to set a proper PORTDIR_OVERLAY entry '
                            'in file ' + self.path +'! Did not overwrite the file.')
        self.write_file(content)
        return True

    def write_file(self, content, backup = False):
        """Write the content to the pre-determined path"""
        path = self.path
        if backup:
            path += '.bak'
        try:
            make_conf = codecs.open(path, 'w', 'utf-8')
            make_conf.write(content)
            make_conf.close()
        except Exception, error:
            raise Exception('MAKE_CONF: write_file(); Failed to write "' + path + '".\nError was:\n'
                            + str(error))
        return True

    def write_property(self, property, values):
        '''  Write the list of property values to /etc/make.conf.'''
        #dprint("SET_CONFIG: MakeConf write_property \n%s' %s = %s" % (property, len(values), values))
        new = property +'="'
        line = ''
        for i in values:
            if len(line) > 60:
                new += line + '\n'
                line = i + ' '
            else:
                line += i + ' '
        new += line +'"\n'
        #dprint("SET_CONFIG: MakeConf write_property \n%s' = %s" % (property, new))
        content = self.regex[property].sub(new, self.data)
        if not self.regex[property].search(content):
            raise Exception('MAKE_CONF: write_property(); failed to set a proper ' + property +' entry '
                            'in file ' + self.path +'! Did not overwrite the file.')
        self.write_file(content)
        return True

    def content(self):
        '''Returns the content of the /etc/make.conf file.'''
        if os.path.isfile(self.path):
            try:
                make_conf = codecs.open(self.path, 'r', 'utf-8')
                self.data = make_conf.read()
                make_conf.close()
            except Exception, error:
                raise Exception('MAKE_CONF: content(); Failed to read "' + self.path + '".\nError was:\n'
                                + str(error))
            self.get_property_list()

    def backup_file(self):
        """backs up the file specified by the initialized path"""
        self.content()
        self.write_file(self.data, backup = True)
        return True

    def get_property_list(self):
        """returns a list of the detected properties in the file"""
        if self.data == '':
            self.content()
        self.properties = []
        lines = self.data.split('\n')
        for line in lines:
            if not line.startswith('#'):
                if '=' in line:
                    self.properties.append(line.split('=')[0])

    def get_properties(self):
        """Parses /etc/make.conf into a dictionary of items with
            dict[setting] = properties list"""
        if not self.properties:
            self.get_property_list()
        for propertiy in self.properties:
                if property == 'PORTDIR_OVERLAY':
                    dict[property] = self.read_overlay()
                else:
                    dict[property] = self.read_property(property)
        return dict

    def add_string_property(self, property, value):
        """Adds the new property and its value to the loaded file data"""
        self.data += ('\n' +property + '=' + value +'\n')

    def add_num_property(self, property, value):
        """Adds the new property and its value to the loaded file data"""
        self.data += ('\n' +property + '=' + str(value) +'\n')


if __name__ == "__main__":

    DATA_PATH = "/usr/share/porthole/"

    from sys import argv, exit, stderr
    from getopt import getopt, GetoptError

    try:
        opts, args = getopt(argv[1:], "lvdf:n:e:a:r:p:c:R:P", ["local", "version", "debug"])
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
    comment = ''

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
        elif opt in ('-c'):
            comment = arg
            dprint("comment = %s" % str(comment))

    if 'make.conf' in file:
        set_make_conf(property, add, remove, replace)
    elif 'package.mask' in file:
        set_package_mask(file, name, ebuild, comment, remove)
    else:
        set_user_config(file, name, ebuild, comment, add, remove)
