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
from xml.sax.handler import *
from re import compile, sub
from os.path import exists

# precompile regexps
re1 = compile("^\s+|\s+$")
re2 = compile("\s+")
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
    def startDocument(self):
        self.path = [];  self.texts = []
        self.result = Metadata()

    def startElement(self, name, attrs):
        self.path.append(name)
        self.texts.append([])
        if name == "maintainer":
            self.result.maintainers.append({})
        # Todo: handle "lang" and "restrict" attributes

    def characters(self, content):
        self.texts[-1] += [content]
        
    def endElement(self, name):
        self.path.pop()
        text = normalize_whitespace("".join(self.texts.pop()))
        if name == "longdescription":
            self.result.longdescription = text
        elif name == "herd":
            self.result.herds.append(text)
        elif self.path and self.path[-1] == "maintainer":
            self.result.maintainers[-1][name] = text
        
# init globals
parser = make_parser()
# no validation or any of that; it takes too much time
for feature in all_features:
    parser.setFeature(feature, False)
handler = MetadataHandler()
parser.setContentHandler(handler)

def parse_metadata(filename):
    """Read a portage metadata file and return a Metadata object."""
    if not exists(filename):
        raise Exception('Metadata file "' + filename + '" does not exist.')
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
