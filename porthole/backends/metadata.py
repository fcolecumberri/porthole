#!/usr/bin/env python

"""
    Portagelib Metadata Library
    Reads metadata info on packages

    Copyright (C) 2003 - 2008 Fredrik Arnerup and Daniel G. Taylor

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
print "METADATA: id initialized to ", id

from xml.sax import make_parser
from xml.sax.handler import *
from re import compile, sub
from os.path import exists
from gettext import gettext as _

# precompile regexps
re1 = compile("^\s+|\s+$")
re2 = compile("\s+")

#Define constants for the two states we care about
ALLOW_CONTENT = 1
SUPPRESS_CONTENT = 2

# fixme  use the Prefs setting if that data is available in the metadata
LANG = 'en'

def normalize_whitespace(text):
    """Remove space at beginning and end
    of string and replace all other whitespace with a single space."""
    return re1.sub("", re2.sub(" ", text))
    #return sub("^\s+|\s+$", "", sub("\s+", " ", text))

class Metadata:
    """Represents the information in the metadata file."""
    def __init__(self):
        self.longdescription = None
        self.herds = []
        self.maintainers = []

class MetadataHandler(ContentHandler):
    
    def __init__(self, target):
        self.target_lang = target
        return

    def startDocument(self):
        self.path = [];  self.texts = []
        self.result = Metadata()
        #Set the initial state, and set up the stack of states
        self._state = ALLOW_CONTENT
        self._state_stack = [ALLOW_CONTENT]
        return

    def startElement(self, name, attrs):
        # Check if there is any language attribute
        lang = attrs.get('lang')
        #dprint("METADATA: lang = %s" %lang)
        if lang:
            # Set the state as appropriate
            if lang[:2] == self.target_lang:
                #dprint("METADATA: target_lang found!")
                self._state = ALLOW_CONTENT
            else:
                self._state = SUPPRESS_CONTENT
        else:
            #dprint("METADATA: no lang attribute")
            self._state = ALLOW_CONTENT
        # Always update the stack with the current state
        # Even if it has not changed
        self._state_stack.append(self._state)
        # Only add the event if the state warrants it
        if self._state == ALLOW_CONTENT:
            self.path.append(name)
            #dprint("METADATA: "name = %s" %name)
            #self.texts.append([''])
            if name == "maintainer":
                self.result.maintainers.append({})
        # Todo: handle "restrict" attributes

    def characters(self, content):
        # Only save the content if the state warrants it
        if self._state == ALLOW_CONTENT and content:
            #dprint("METADATA: content = %s" %content)
            self.texts = self.texts + [content]
            #dprint("METADATA: self.texts = ")
            #dprint( self.texts)
        #else:
            #dprint("METADATA: SUPPRESS_CONTENT")
        
    def endElement(self, name):
        #dprint("METADATA: end element")
        self._state = self._state_stack.pop()
        #Only complete the event if the state warrants it
        if self._state == ALLOW_CONTENT:
            #self._downstream.endElement(name)
            self.path.pop()
            #text = normalize_whitespace("".join(self.texts.pop()))
            text = normalize_whitespace("".join(self.texts))
            self.texts = []
            #dprint("METADATA: end element name = %s" %name)
            #dprint("METADATA: end element text = %s" %text)
            if name == "longdescription":
                #dprint("METADATA: end element found longdescription")
                self.result.longdescription = text
            elif name == "herd":
                self.result.herds.append(text)
            elif self.path and self.path[-1] == "maintainer":
                self.result.maintainers[-1][name] = text
        return
        
# init globals
parser = make_parser()
# no validation or any of that; it takes too much time
for feature in all_features:
    parser.setFeature(feature, False)

# need to add a prefs.lang parameter instead of hardcoding
handler = MetadataHandler(LANG)
parser.setContentHandler(handler)

def parse_metadata(filename):
    """Read a portage metadata file and return a Metadata object."""
    if not exists(filename):
        raise Exception(_('Metadata file "%s" does not exist.') % filename)
    parser.parse(filename)
    return handler.result



if __name__ == '__main__':
    def main():
        from sys import argv
        metadata = parse_metadata(argv[1])
        print "Long description:", metadata.longdescription
        print "Herds:", metadata.herds
        print "Maintainers:", metadata.maintainers

    import profile, pstats
    from sys import stdout
    profile.run("main()", "stats.txt")

    stats = pstats.Stats("stats.txt")
    stats.strip_dirs()
    #stats.sort_stats('cumulative')
    stats.sort_stats('time')
    #stats.sort_stats('calls')
    stats.print_stats(0.1)
