#!/usr/bin/env python

"""
    Porthole XML Manager Module

    Copyright (C) 2004 - 2008 Wm. F. Wheeler

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

import xml.sax
from xml.sax.saxutils import XMLFilterBase, XMLGenerator

#Define constants for the two states we care about
ALLOW_CONTENT = 1
SUPPRESS_CONTENT = 2

class LangFilter(XMLFilterBase):
    def __init__(self, upstream, downstream, target_lang):
        XMLFilterBase.__init__(self, upstream)
        self._downstream = downstream
        self.target_lang = target_lang
        return

    def startDocument(self):
        #Set the initial state, and set up the stack of states
        self._state = ALLOW_CONTENT
        self._state_stack = [ALLOW_CONTENT]
        return

    def startElement(self, name, attrs):
        #Check if there is any language attribute
        lang = attrs.get('lang')
        if lang:
            #Set the state as appropriate
            if lang[:2] == self.target_lang:
                self._state = ALLOW_CONTENT
            else:
                self._state = SUPPRESS_CONTENT
        #Always update the stack with the current state
        #Even if it has not changed
        self._state_stack.append(self._state)
        #Only forward the event if the state warrants it
        if self._state == ALLOW_CONTENT:
            self._downstream.startElement(name, attrs)
        return

    def endElement(self, name):
        self._state = self._state_stack.pop()
        #Only forward the event if the state warrants it
        if self._state == ALLOW_CONTENT:
            self._downstream.endElement(name)
        return

    def characters(self, content):
        #Only forward the event if the state warrants it
        if self._state == ALLOW_CONTENT:
            self._downstream.characters(content)
        return


if __name__ == "__main__":
    parser = xml.sax.make_parser()
    #XMLGenerator is a special SAX handler that merely writes
    #SAX events back into an XML document
    downstream_handler = XMLGenerator()
    #upstream, the parser, downstream, the next handler in the chain
    filter_handler = LangFilter(parser, downstream_handler, 'en')
    import sys
    #The SAX filter base is designed so that the filter takes
    #on much of the interface of the parser itself, including the
    #"parse" method
    filter_handler.parse(sys.argv[1])
