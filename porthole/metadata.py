#!/usr/bin/env python

"""
    Portagelib Metadata Library
    Reads metadata info on packages

    Copyright (C) 2003 Fredrik Arnerup and Daniel G. Taylor

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

from xml.sax import make_parser
from xml.sax.saxutils import DefaultHandler
from xml.sax.handler import feature_namespaces
from re import sub
from os.path import exists

def normalize_whitespace(text):
    """Remove space at beginning and end
    of string and replace all other whitespace with a single space."""
    return sub("^\s+|\s+$", "", sub("\s+", " ", text))

class Metadata:
    """Represents the information in the metadata file."""
    def __init__(self):
        self.longdescription = None
        self.herds = []
        self.maintainers = []

class MetadataHandler(DefaultHandler):
    def __init__(self):
        self.path = [];  self.texts = []
        self.result = Metadata()

    def startElement(self, name, attrs):
        self.path.append(name)
        self.texts.append("")
        if name == "maintainer":
            self.result.maintainers.append({})
        # Todo: handle "lang" and "restrict" attributes

    def characters(self, content):
        self.texts[-1] += content
        
    def endElement(self, name):
        self.path.pop()
        text = normalize_whitespace(self.texts.pop())
        if name == "longdescription":
            self.result.longdescription = text
        elif name == "herd":
            self.result.herds.append(text)
        elif self.path and self.path[-1] == "maintainer":
            self.result.maintainers[-1][name] = text
        
        
def parse_metadata(filename):
    """Read a portage metadata file and return a Metadata object."""
    if not exists(filename):
        raise Exception('Metadata file "' + filename + '" does not exist.')
    parser = make_parser()
    parser.setFeature(feature_namespaces, 0)
    handler = MetadataHandler()
    parser.setContentHandler(handler)
    parser.parse(filename)
    return handler.result



if __name__ == '__main__':
    from sys import argv
    metadata = parse_metadata(argv[1])
    print "Long description:", metadata.longdescription
    print "Herds:", metadata.herds
    print "Maintainers:", metadata.maintainers
