#!/usr/bin/env python

'''
    Porthole Utils Package
    Holds common functions for Porthole

    Copyright (C) 2003 - 2005 Fredrik Arnerup, Daniel G. Taylor
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

import sre

from _xml.xmlmgr import XMLManager, XMLManagerError
from gettext import gettext as _
#import utils.debug



class PortholeConfiguration:
    """ Holds all of Porthole's developer configurable settings """
    def __init__(self):
        self.DATA_PATH = ''

    def set_path(self, DATA_PATH):
        self.DATA_PATH = DATA_PATH
        
    def load(self):
        dom = XMLManager(self.DATA_PATH + 'config/configuration.xml')

        # Handle all the regular expressions.  They will be compiled
        # within this object for the sake of efficiency.
        
        filterlist = ['info', 'warning', 'error', 'caution', 'needaction']
        for filter in filterlist:
            patternlist = dom.getitem(''.join(['/re_filters/',filter])) # e.g. '/re_filters/info'
            attrname = ''.join([filter, '_re_list'])
            setattr(self, attrname, []) # e.g. self.info_re_list = []
            for regexp in patternlist:
                getattr(self, attrname).append(sre.compile(regexp))
            patternlist = dom.getitem(''.join(['/re_filters/not',filter])) # e.g. '/re_filters/notinfo'
            attrname = ''.join([filter, '_re_notlist'])
            setattr(self, attrname, []) # e.g. self.info_re_notlist = []
            for regexp in patternlist:
                getattr(self, attrname).append(sre.compile(regexp))
        
        self.emerge_re = sre.compile(dom.getitem('/re_filters/emerge'))
        self.ebuild_re = sre.compile(dom.getitem('/re_filters/ebuild'))
        self.merged_re = sre.compile(dom.getitem('/re_filters/merged'))
        del dom

    def isInfo(self, teststring):
        ''' Parse string, return true if it matches info
            reg exp and its not in the reg exp notlist'''
        for regexp in self.info_re_list:
            if regexp.match(teststring):
                for regexpi in self.info_re_notlist:
                    if regexpi.match(teststring):
                        return False    # excluded, no match
                return True
        return False

    def isWarning(self, teststring):
        ''' Parse string, return true if it matches warning reg exp '''
        for regexp in self.warning_re_list:
            if regexp.match(teststring):
                for regexpi in self.warning_re_notlist:
                    if regexpi.match(teststring):
                        return False    # excluded, no match
                return True
        return False

    def isCaution(self, teststring):
        ''' Parse string, return true if matches caution regexp '''
        for regexp in self.caution_re_list:
            if regexp.match(teststring):
                for regexpi in self.caution_re_notlist:
                    if regexpi.match(teststring):
                        return False    # excluded, no match
                return True
        return False

    def isError(self, teststring):
        ''' Parse string, return true if belongs in error tab '''
        for regexp in self.error_re_list:
            if regexp.match(teststring):
                for regexpi in self.error_re_notlist:
                    if regexpi.match(teststring):
                        return False    # excluded, no match
                return True
        return False

    def isEmerge(self, teststring):
        ''' Parse string, return true if it is the initial emerge line '''
        return self.emerge_re.match(teststring) != None

    def isMerged(self, teststring):
        ''' Parse string, return true if it is the merged line '''
        return self.merged_re.search(teststring) != None
    def isAction(self, teststring):
        '''
        Returns True if teststring matches the pre-set criteria for notification of an
        action the user is recommended to take, such as etc-update or revdep-rebuild.
        '''
        for regexp in self.needaction_re_list:
            if regexp.match(teststring):
                for regexpi in self.needaction_re_notlist:
                    if regexpi.match(teststring):
                        return False    # excluded, no match
                return True
        return False