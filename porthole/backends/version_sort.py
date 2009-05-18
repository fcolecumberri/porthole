#!/usr/bin/env python

'''
    Porthole's Version string list sorting functions that follows portages
    rules for comparing versions.  The pad_ver() is modified from
    the soon to be implemented portage.vercmp()

    Copyright (C) 2003 - 2008 Fredrik Arnerup, Brian Dolbec, 
    Daniel G. Taylor and Wm. F. Wheeler

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
'''

import datetime
id = datetime.datetime.now().microsecond
print "VERSION_SORT: id initialized to ", id

if __name__ == "__main__":
    
    # setup our path so we can load our custom modules
    from sys import path
    path.append('/home/brian/porthole')
    from sys import argv, exit, stderr
    from getopt import getopt, GetoptError

import re


from porthole.utils.debug import dprint
from porthole import config
#~ from porthole.importer import my_import
#~ comps = config.Prefs.PORTAGE.split('.')
#~ print comps
#~ if comps[0] in 'backends':
   #~ comps = comps[1:]
#~ print comps
#~ name = '.'.join(comps)
    
#~ portage_lib = my_import(name)

## circular import problem
##from porthole import backends
##portage_lib = backends.portage_lib

############### new code ###############

ver_regexp = re.compile("^(cvs-)?(\\d+)((\\.\\d+)*)([a-zA-Z]?)((_(pre|p|beta|alpha|rc)\\d*)*)(-r(\\d+))?$")
suffix_regexp = re.compile("^(alpha|beta|rc|pre|p)(\\d*)$")
# modified portage comparison suffix values for sorting in desired precedence
suffix_value = {"alpha": '0', "beta": '1', "pre": '2', "rc": '3', "p": '4'}

# most version numbers will not exceed 2 digits, but make it 3 just in case
fill_size = 3

def pad_ver(vlist):
    """pads the version string so all number sequences are the same
       length for acurate sorting, borrowed & modified code from new portage vercmp()"""
    #dprint("VERSION_SORT:  pad_ver();  vlist[]")
    #dprint(vlist)
    # short circuit for  list of 1
    #if len(vlist) == 1:
    #    return vlist

    max_length = 0

    suffix_count = 0
    # suffix length may have dates for version number (8) so make it 2 extra just in case
    suffix_length = 10
    # the lack of a suffix would imply the smallest value possible for it
    suffix_pad = "0"

    val_cache = []

    #dprint("VERSION_SORT: pad_ver(); checking maximum length value of version pattern") 
    for x in vlist:
        #dprint(x)
        max_length = max(max_length, x.count('.'))
        suffix_count = max(suffix_count, x.count("_"))

    #dprint("VERSION_SORT: pad_ver(); max_length = %d, suffix_count =%d" \
    #       %(max_length, suffix_count))

    for val1 in vlist:
        #dprint("VERSION_SORT: pad_ver(); new val1 = %s" %val1)
        match1 = ver_regexp.match(val1)
        # checking that the versions are valid
        if not match1 or not match1.groups():
            dprint("VERSION_SORT: pad_ver(); !!! syntax error in version:")
            dprint(val1)
            return None

        # building lists of the version parts before the suffix
        # first part is simple
        list1 = [match1.group(2).zfill(fill_size)]

        # extend version numbers
        # this part would greatly benefit from a fixed-length version pattern
        if len(match1.group(3)):
            vlist1 = match1.group(3)[1:].split(".")
            for i in range(0, max_length):
                if len(vlist1) <= i or len(vlist1[i]) == 0:
                    list1.append("0".zfill(fill_size))
                else:
                    list1.append(vlist1[i].zfill(fill_size))

        # and now the final letter
        #dprint("VERSION_SORT: pad_ver(); final letter")
        if len(match1.group(5)):
            list1.append(match1.group(5))
        else: # add something to it in case there is a letter in a vlist member
            list1.append("!") # "!" is the first visible printable char

        # main version is done, so now the _suffix part
        #dprint("VERSION_SORT: pad_ver(); suffix part")
        list1b = match1.group(6).split("_")[1:]

        for i in range(0, suffix_count):
            s1 = None
            if len(list1b) <= i:
                s1 = str(suffix_value["p"]) + suffix_pad.zfill(suffix_length)
            else:
                slist = suffix_regexp.match(list1b[i]).groups()
                s1 = str(suffix_value[slist[0]]) + slist[1].zfill(suffix_length)
            if s1:
                #dprint("VERSION_SORT: pad_ver(); s1")
                #dprint(s1)
                list1 += [s1]
                
        # the suffix part is done, so finally the revision
        #dprint("VERSION_SORT: pad_ver(); revision part")
        r1 = None
        if match1.group(10):
            r1 = 'r' + match1.group(10).zfill(fill_size)
        else:
            r1 ='r' + "0".zfill(fill_size)
        if r1:
            list1 += [r1]

        # reconnect the padded version string
        result = ''
        for y in list1:
            result += y
        #dprint("VERSION_SORT: pad_ver(); result= %s" %result)

        # store the padded version
        val_cache += [result]

    #dprint(val_cache)
    #dprint("VERSION_SORT: pad_ver(); done")
    return val_cache

def two_list_sort(keylist, versions):
    """sorts the versions list using the keylist values"""
    #dprint("VERSION_SORT: two_list_sort() ; keylist, versions")
    #dprint(keylist)
    #dprint(versions)
    dbl_list = {}
    for x in range(0,len(versions)):
        dbl_list[keylist[x]] =  versions[x]

    # Sort the versions using the padded keylist
    keylist.sort()

    #rebuild versions in sorted order
    result = []
    for key in keylist:
        result += [dbl_list[key]]
    return result

def ver_sort(versions):
    """sorts a version list according to portage versioning rules"""
    if len(versions) <2:  # no need to sort for 0 or 1 versions
        return versions
    keylist = pad_ver(get_versions_only(versions))
    if not keylist: # there was an error
        dprint("VERSION_SORT: ver_sort(); keylist[] creation error")
        return (versions + ["error_in_sort"]) 
    sorted = two_list_sort(keylist, versions)
    #dprint("VERSION_SORT: ver_sort(); complete!")
    return sorted

def get_versions_only(versions):
    """inputs a cat/pkg-version list and returns a version list"""
    #dprint("VERSION_SORT: get_versions()")
    # convert versions into the padded version only list
    from porthole import backends
    portage_lib = backends.portage_lib
    vlist = []
    for v in versions:
        #dprint(v)
        vlist += [portage_lib.get_version(v)]
        #dprint(vlist)
    return vlist


def ver_match(versions, range1, range2 = None):
    """looks for a version match in range1 and optionaly in range2"""
    if not versions:
        return None
    plist = pad_ver(get_versions_only(versions))
    r1 = pad_ver(range1)
    if range2:
        r2 = pad_ver(range2)
    if not plist:
        dprint("VERSION_SORT: ver_match(); plist[] creation error")
        return False, False
    match1 = False
    match2 = False
    for x in plist:
        if (x >= r1[0] and x <= r1[1]):
            dprint("VERSION_SORT: ver_match(); match1 %s, %s:%s" %(x,r1[0],r1[1]))
            match1 = True
        if range2 and (x >= r2[0] and x <= r2[1]):
            dprint("VERSION_SORT: ver_match(); match2 %s, %s:%s" %(x,r2[0],r2[1]))
            match2 = True
    return match1, match2

if __name__ == "__main__":
 
    versions = ['net-mail/some_package-1.1','net-mail/some_package-1.0',
                'net-mail/some_package-1.21','net-mail/some_package-1.21.1',
                'net-mail/some_package-1.1-r1','net-mail/some_package-1.0_pre1',
                'net-mail/some_package-1.3.1_rc2','net-mail/some_package-1.1a',
                'net-mail/some_package-1.23.4_pre2','net-mail/some_package-1.3.1_p1',
                'net-mail/some_package-1.1a-r2','net-mail/some_package-1.21.2'
                ]

    sorted = ver_sort(versions)
    dprint("VERSION_SORT: new sorted version list")
    dprint(sorted)



    
