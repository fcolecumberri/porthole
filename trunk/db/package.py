#!/usr/bin/env python

'''
    Porthole Package class
    Basic data structure and direct support functions for a gentoo package

    Copyright (C) 2003 - 2006 Fredrik Arnerup, Daniel G. Taylor
    Brian Dolbec, Wm. F. Wheeler, Tommy Iorns

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

#from backends import portage_lib
from backends.version_sort import ver_sort

import utils.debug
import backends
portage_lib = backends.portage_lib

REFRESH = True

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
        self.in_world = full_name in portage_lib.World
        self.is_checked = False
        self.depricated = False

    def in_list(self, list=None):
        """returns True/False if the package is listed in the list"""
        #utils.debug.dprint("Package.in_list: %s" %self.full_name)
        #utils.debug.dprint("Package.in_list: %s" %str(list))
        if self.full_name == "None":
            return False
        if list == "World":
            return self.in_world
        elif list == "Dependencies":
            #  redundant I know, but this method leaves room for adding an "Orphaned"  listing next
            return not self.in_world
        elif list:
            #utils.debug.dprint("Package.in_list: " + str(self.full_name in list))
            # insert routine for checking if the package is in the specified list
            return self.full_name in list
        return False
            

    def update_info(self):
        """Update the package info"""
        if self.full_name == "None":
            return
        self.is_upgradeable(REFRESH)
        self.in_world = full_name in portage_lib.World

    def get_installed(self, refresh = False):
        """Returns a list of all installed ebuilds."""
        if self.full_name == "None":
            return []
        if self.installed_ebuilds == None or refresh:
            self.installed_ebuilds = portage_lib.get_installed(self.full_name)
        return self.installed_ebuilds
    
    def get_name(self):
        """Return name portion of a package"""
        if self.full_name == "None":
            return self.full_name
        if self.name == None:
            self.name = portage_lib.get_name(self.full_name)
        return self.name

    def get_category(self):
        """Return category portion of a package"""
        if self.full_name == "None":
            return ''
        if self.category == None:
            self.category = portage_lib.get_category(self.full_name)
        return self.category

    def get_latest_ebuild(self, include_masked = False):
        """Return latest ebuild of a package"""
        # Note: this is slow, see get_versions()
        # Note: doesn't return hard-masked packages by default, unless in package.unmask
        # unstable packages however ARE returned. To return the best version for a system,
        # taking into account keywords and masking, use get_best_ebuild().
        if self.full_name == "None":
            return ''
        # next one was a pointer to portage's cache so removing masked ebuilds screwed things up
        vers = self.get_versions()[:]  # make a local copy. portage fixed in svn r5382
        utils.debug.dprint("PACKAGE: get_latest_ebuild(); versions: " + str(vers)) 
        if include_masked:
            utils.debug.dprint("PACKAGE: get_latest_ebuild(); trying portage_lib.best() of versions: " + str(vers)) 
            return portage_lib.best(vers)
        if self.latest_ebuild == None:
            utils.debug.dprint("PACKAGE: get_latest_ebuild(); checking hard masked vers = " + str(vers)) 
            for m in self.get_hard_masked(check_unmask = True):
                while m in vers:
                    vers.remove(m)
            self.latest_ebuild = portage_lib.best(vers)
        return self.latest_ebuild

    def get_best_ebuild(self, refresh = False):
        """Return best visible ebuild (taking account of package.keywords, .mask and .unmask.
        If all ebuilds are masked for your architecture, returns ''."""
        if self.full_name == "None":
            return ''
        if self.best_ebuild == None or refresh:
            self.best_ebuild = portage_lib.get_best_ebuild(self.full_name)
            utils.debug.dprint("PACKAGE: get_best_ebuild();  = " + str(self.best_ebuild)) 
        return self.best_ebuild

    def get_default_ebuild(self):
        if self.full_name == "None":
            return ''
        return (self.get_best_ebuild() or
                self.get_latest_ebuild() or
                self.get_latest_ebuild(include_masked = True) or
                self.get_latest_installed())

    def get_size(self, ebuild = None):
        if self.full_name == "None":
            return ''
        if self.size == None or ebuild:
            if not ebuild:
                ebuild = self.get_default_ebuild()
                if ebuild: self.size = portage_lib.get_size(ebuild)
                else: 
                    self.size = ''
                    return self.size
            else: # return the specific ebuild size
                return portage_lib.get_size(ebuild)
        
    def get_digest(self):
        if self.full_name == "None":
            return ''
        if self.digest_file == None:
            self.digest_file = portage_lib.get_digest( self.get_latest_ebuild() )
        return self.digest_file

    def get_latest_installed(self, refresh = False):
        if self.full_name == "None":
            return ''
        if self.latest_installed == None or refresh:
            installed_ebuilds = self.get_installed(refresh )
            if len(installed_ebuilds) == 1:
                return installed_ebuilds[0]
            elif len(installed_ebuilds) == 0:
                return ""
            installed_ebuilds = ver_sort( installed_ebuilds )
            self.latest_installed = installed_ebuilds[-1]
        return self.latest_installed

    def get_description(self):
        if self.properties:
            return self.properties[self.get_default_ebuild()].description
        return self.get_properties().description

    def get_metadata(self):
        """Get a package's metadata, if there is any"""
        if self.full_name == "None":
            return ''
        return portage_lib.get_metadata(self.full_name)

    def get_properties(self, specific_ebuild = None):
        """ Returns properties of specific ebuild.
            If no ebuild specified, get latest ebuild. """
        #utils.debug.dprint("PACKAGE: get_properties()")
        if self.full_name == "None":
            return ''
        if specific_ebuild == None:
            ebuild = self.get_default_ebuild()
            if not ebuild:
                utils.debug.dprint("PACKAGE; get_properties(): No ebuild found for %s!" % self.full_name)
                #raise Exception(_('No ebuild found.'))
        else:
            #utils.debug.dprint("PACKAGE: get_properties(); Using specific ebuild")
            ebuild = specific_ebuild
        if not ebuild in self.properties:
            #utils.debug.dprint("PACKAGE: geting properties for '%s'" % str(ebuild))
            self.properties[ebuild] = portage_lib.get_properties(ebuild)
        return self.properties[ebuild]

    def get_versions(self, include_masked = True):
        """Returns all available ebuilds for the package"""
        if self.full_name == "None":
            return ''
        # Note: this is slow, especially when include_masked is false
        criterion = include_masked and 'match-all' or 'match-visible'
        utils.debug.dprint("PACKAGE: get_versions(); criterion = %s, package = %s" %(str(criterion),self.full_name))
        v = portage_lib.get_versions(self.full_name)
        utils.debug.dprint("PACKAGE: get_versions(); v = " + str(v))
        return v

    def get_hard_masked(self, check_unmask = False):
        """Returns all versions hard masked by package.mask.
        if check_unmask is True, it excludes packages in package.unmask"""
        if self.full_name == "None":
            return ''
        if self.hard_masked_nocheck == None:
            self.hard_masked_nocheck, self.hard_masked = portage_lib.get_hard_masked(self.full_name)
        if check_unmask: return self.hard_masked
        else: return self.hard_masked_nocheck
        

    def is_upgradable(self, refresh = False):
        """Indicates whether an unmasked upgrade/downgrade is available.
        If portage wants to upgrade the package, returns 1.
        If portage wants to downgrade the package, returns -1.
        Else, returns 0.
        """
        if self.full_name == "None":
            return 0
        if self.upgradable == None or refresh:
            best = self.get_best_ebuild(refresh)
            installed = self.get_latest_installed(refresh)
            if not best or not installed:
                self.upgradable = 0
                return self.upgradable
            better = portage_lib.best([best,installed])
            if best == installed:
                self.upgradable = 0
            elif better == best:
                self.upgradable = 1
            elif better == installed:
                self.upgradable = -1
        return self.upgradable

