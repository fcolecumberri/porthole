# -*- coding: utf-8 -*-
#
""" File: porthole/views/hightlight.py
This file is part of the Porthole, a graphical portage-frontend.

Copyright (C) 2006-2009 René 'Necoro' Neumann
This is free software.  You may redistribute copies of it under the terms of
the GNU General Public License version 2.
There is NO WARRANTY, to the extent permitted by law.

Written by René 'Necoro' Neumann <necoro@necoro.net>
Adapted to Porthole by, Brian Dolbec <dol-sen@users.sourceforge.net>
"""
from __future__ import absolute_import, with_statement

import gtksourceview2
#import logging

from porthole.utils import debug
from porthole.views.lazyview import LazyView


class HighlightView (gtksourceview2.View, LazyView):

    def __init__ (self, get_file_fn, languages = []):
        """@param get_file_fn: function to return a filename from a pkg object
            @param get_file_fn: if None, then it will use pkg as the filename to show
            @param languages: list of languages to use for highlighting eg. ['gentoo', 'shell']
        """
        if get_file_fn:
            self.get_fn = get_file_fn
        else:  # assume it is passed a filename already
            self.get_fn = self._get_fn

        man = gtksourceview2.LanguageManager()
        
        language = None
        old_lang = None
        for lang in languages:
            if old_lang:
                debug.dprint("HIGHLIGHT: No %(old)s language file installed. Falling back to %(new)s." %{"old" : old_lang, "new" : lang})
            
            language = man.get_language(lang)
            if language:
                break
            else:
                old_lang = lang

        if not language and old_lang:
            debug.dprint("HIGHLIGHT: No %(old)s language file installed. Disable highlighting." %{"old" : old_lang})

        buf = gtksourceview2.Buffer()
        buf.set_language(language)

        gtksourceview2.View.__init__(self, buf)
        LazyView.__init__(self)

        self.set_editable(False)
        self.set_cursor_visible(False)

    def _get_fn(self, x):
        return x

    def set_text (self, text):
        self.get_buffer().set_text(text)
    
    def _get_content (self):
        try:
            debug.dprint("HIGHLIGHT: filename to load: " + self.get_fn(self.pkg))
            with open(self.get_fn(self.pkg)) as f:
                return f.readlines()
        except IOError, e:
            return "Error: %s" % e.strerror
