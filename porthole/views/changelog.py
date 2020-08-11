# -*- coding: utf-8 -*-
#
""" File: porthole/views/changelog.py
This file is part of the Porthole, a graphical portage-frontend.

Copyright (C) 2009 Brian Dolbec <dol-sen>
This is free software.  You may redistribute copies of it under the terms of
the GNU General Public License version 2.
There is NO WARRANTY, to the extent permitted by law.

Written by, Brian Dolbec <dol-sen@users.sourceforge.net>
"""
#from __future__ import absolute_import, with_statement

import os.path
#import logging
import re

from porthole.utils import debug
from porthole.views.list import ListView
from porthole.views.markup import MarkupView
from porthole import backends
from porthole.loaders.loaders import load_web_page


class ChangeLogView (ListView, MarkupView):
    """ChangeLog subclass which adds bug# highlighting and opening in
    the defined webbrowser

    example use:
    from porthole.views.changelog import ChangeLogView
    myview = ChangeLogView()
    myview.update(ebuild)

    """

    bug_re = re.compile(r'\d{4,}')
    atom_re = re.compile(r'\S+\-\d+\S+')
    word_re = [atom_re, bug_re]
    word_fn = ['atom', 'bug']
    new_ver_re = re.compile(r'(?P<atom>\*.*) (?P<date>\(.*\))')
    update_re = re.compile(r'(?P<date>\d\d [A-Z][a-z][a-z] \d\d\d\d;) (?P<developer>.*[<]\S+[>]) (?P<text>.*)')
    # could probably tweak the code to not require the update_re and use update_re2 and search the
    # remaining text for atoms, bug's
    update_re2 = re.compile(r'(?P<date>\d\d [A-Z][a-z][a-z] \d\d\d\d;) (?P<developer>.*[<]\S+[>])')
    all = re.compile(r'(?P<text>.*)')
    re_list = [new_ver_re, update_re, update_re2, all]
    re_fn = ['new_ver', 'update',  'update2', 'all']

    def __init__ (self):

        ListView.__init__(self, self._get_fn)
        MarkupView.__init__(self)

        self.bugzilla_url = "http://bugs.gentoo.org/show_bug.cgi?id="
        self.bugs = {}
        self.bug_id = 0

        self.indent = ' '*4



    def _get_fn(self, cpv):
        """Returns a path to the specified category/package-version ChangeLog"""
        dir, file = os.path.split(backends.portage_lib.get_path(cpv))
        if dir:
            return os.path.join(dir, "ChangeLog")
        return ''

    def set_text(self, text):
        debug.dprint("ChangeLogView: set_text(); len(text) = %d" %len(text))
        self.buffer.set_text('')
        if not text:
            return
        lines = text.split('\n')
        while lines[0].startswith('#'):
            self.append(lines[0], "header")
            self.nl()
            lines = lines[1:]
        for line in lines:
            found = None
            x = -1
            while not found and x < len(self.re_list)-1:
                if line == '\n':
                    self.nl()
                    break
                x += 1
                found = (self.re_list[x]).match(line.strip())
                #debug.dprint("ChangeLogView: set_text(), checking for: %s" %self.re_fn[x])
            if found and found.groupdict():
                mydict = found.groupdict()
                #debug.dprint("ChangeLogView: set_text(), mydict = %s" %str(mydict))
            # process the parts
            getattr(self, '_%s_' %self.re_fn[x])(mydict)
        return

    def _new_ver_(self, parts):
        #debug.dprint("ChangeLogView: _new_ver_(), parts = %s" %str(parts))
        self.append(parts['atom'], 'new_ver')
        self.append_date(parts['date'])
        self.nl()
        return

    def _update_(self, parts):
        #debug.dprint("ChangeLogView: _update_(), parts = %s" %str(parts))
        self.append_date(parts['date'], self.indent)
        self.append(' ')
        self.append_developer(parts['developer'])
        self.append(' ')
        if self.atom_re.match(parts['text']):
            self.append_atom(parts['text'])
        else:
            self.append(parts['text'])
        self.nl()

    def _update2_(self, parts):
        #debug.dprint("ChangeLogView: _update2_(), parts = %s" %str(parts))
        self.append_date(parts['date'], self.indent)
        self.append(' ')
        self.append_developer(parts['developer'])
        self.nl()
        return

    def _all_(self, parts):
        #debug.dprint("ChangeLogView: _all_(), parts = %s" %str(parts))
        words = parts['text'].split()
        self.append(self.indent[:-1])
        #debug.dprint("ChangeLogView: _all_(), words = %s" %str(words))
        for word in words:
            self.append(' ')  # spacer between words
            found = None
            x = -1
            while not found and x < len(self.word_re)-1:
                x += 1
                found = (self.word_re[x]).search(word)
                #debug.dprint("ChangeLogView: _all_(), checking for: %s" %self.word_fn[x])
            if found and found.group():
                #debug.dprint("ChangeLogView: _all_(), found = %s, %s" %(self.word_fn[x], found.group()))
                # process the parts
                getattr(self, 'append_%s' %self.word_fn[x])(word)
            else:
                #debug.dprint("ChangeLogView: _all_(), adding as text: " + word)
                self.append(word, 'normal')
        self.nl()
        return

