###############################################################################
# Porthole Project - A Graphical Front-end to Portage
###############################################################################
# File name: xmlmgr.py
#  Abstract: A class to encapsulate XML DOM functionality and simplify the
#            storing of Python variables in an XML format.  Created to save &
#            load user preferences and application configuration info/from
#            XML files.
#  Language: Python 2.3
#------------------------------------------------------------------------------ 
# Legal Information
"""
     Porthole XML Manager Module

     Copyright (C) 2004 - 2008 Wm. F. Wheeler, Brian Dolbec

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
#------------------------------------------------------------------------------ 
# Technical/design Notes:
#
# 1. To conserve memory, del the xmlmanager instance as soon as possible.
# 2. No error checking for opening/closing/overwriting of files is performed.
# 3. Use unique namedef's otherwise items with identical namedefs will be
#    returned as a list of values.
# 4. Namedefs can be constructed heirachically using forward slashes as
#    separators (E.G. prefs/window/x).  The leading and trailing slashes are
#    optional.
# 5. When specifying namedefs, including the root element name is optional.
# 6. __init__(None) creates an empty XML document.  You should set the .name
#    and .version properties before any items are added or the root element &
#    version will default to "xml_mgr" and "1" respectively.
# 7. The following types are supported: bool, int, long, float, complex, str,
#    unicode, list, tuple and dict.  List, tuple and dict can only contain the
#    above named types (including other lists, tuples and dictionaries).
# 8. If you try to retrieve a non-existant node the class will raise an
#    exception that can be trapped (XMLManagerError).
#
#------------------------------------------------------------------------------ 
# References:
#
# 1. Python XML Module Library Reference
#    http://www.python.org/doc/current/lib/
# 2. Dive Into Python - XML processing
#    http://diveintopython.org/xml_processing/index.html
#
###############################################################################

import sys

try:
     from xml.dom.minidom import parse, getDOMImplementation
except Exception, e:
     print >> sys.stderr, "*** Error loading xml.dom.minidom. Original exception was: %s" % e


class XMLManagerError(Exception):
    """XML Manager Error exception class"""
    def __init__(self, arg = None, info = ''):
        self.arg = arg
        self.supplemental = info
    def __str__(self):
        if len(self.supplemental) > 0:
            return str(self.arg) + ": " + self.supplemental
        else:
            return str(self.arg)


class XMLManager:
    """ Simplified XML file parser/reader/writer

        Public properties:
            name - (string) name of the root element
            version - (string) value of ver attribute of root element

        Public methods:
            init__(source) - string with XML file name or None
            getitem(namedef) - returns properly typed value from document 
                stored under namedef 
            additem(namedef,value) - add the specified value under namedef.
            The type of the value is preserved in the XML document.
            save(filename) - write the XML document to the specified file
    """

    def __init__(self, source):
        """ XML class constructor.  
            Parameters: 
                source = string containing the XML file name or None to
                             create an empty DOM
            Returns: xmlmanager object instance
        """
        if source != None:
            try:
                self.__dom = parse(source)
                self.name = self.__dom.documentElement.tagName
                self.version = self.__dom.documentElement.getAttribute('ver')
            except: # possibly a bad/empty file
                print >> sys.stderr, "XMLMGR: Error loading preferences file %s.  Setting to None to load default settings" %source
                self.__dom = None
                self.name = "xml_mgr"
                self.version = "1"
        else:
            self.__dom = None
            self.name = "xml_mgr"
            self.version = "1"


    def __del__(self):
        """ Default destructor """
        if self.__dom:
          self.__dom.unlink()


    def __initDOM(self):
        """ Initialize DOM if it is empty, otherwise exit """
        if self.__dom == None:
            impl = getDOMImplementation()
            self.__dom = impl.createDocument(None, self.name, None)
            
            # Get the root element and set the version attribute

            root = self.__dom.documentElement
            root.setAttribute('ver', self.version)


    def __FindNode(self, path_list, startnode = None):
        """ Find the specified node given in path_list
            Parameters: 
                path_list = path decomposed as a list
                startnode = starting node to search, defaults to DOM root
            Returns: the node or None if not found

             NOTE: This was written because getElementsByTagName() scans
             through all levels of the document and can give misleading
             results when duplicate element names exist across
             multiple levels. 
        """
        if startnode == None:
            try:
                node = self.__dom.documentElement
            except:
                raise XMLManagerError("NodeNotFound", path_list)
        else:
            node = startnode

        level = 0  # start with first list item
        maxlevel = len(path_list)-1  # don't go past end of list
        while level <= maxlevel:
            # skip over empty element names
            if len(path_list[level]) == 0:
                 level += 1
            if node.hasChildNodes():
                found = False
                for x in node.childNodes:
                    if x.nodeType == x.ELEMENT_NODE and x.nodeName == path_list[level]:
                        found = True
                        break
                if found:
                     level += 1  
                     node = x
                else:
                     raise XMLManagerError("NodeNotFound", path_list)
            else:
                raise XMLManagerError("NodeNotFound", path_list)
        return x

    def __NodeText(self,nodelist):
        """ Private function to extract text from child nodes """
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc

    def __InsertValue(self, pnode, nodeName, value):
        """ Private method to convert basic python variable types
             and save them as XML text
        """
        # Create the node to hold the value.
        # Non-string values must be converted to string
        # to be XML compliant.  The py_type attribute records
        # the original value's Python type
    
        newnode = self.__dom.createElement(nodeName)
        node = pnode.appendChild(newnode)

        # Handle None as special case

        if value == None:
            newnode.setAttribute('py_type', 'none')

        # String types
        # Note: check for empty strings, they wreak havoc if you try
        # to use the .createTextNode() & appendChild() methods

        elif type(value) == str:
            if len(value) > 0:
                text = self.__dom.createTextNode(value)
                node.appendChild(text)

        elif type(value) == unicode:
            newnode.setAttribute('py_type', 'unicode')
            if len(value) > 0:
                text = self.__dom.createTextNode(str(value))
                node.appendChild(text)

        # Number types

        elif type(value) == int:
            newnode.setAttribute('py_type', 'int')
            text = self.__dom.createTextNode(str(value))
            node.appendChild(text)

        elif type(value) == long:
            newnode.setAttribute('py_type', 'long')
            text = self.__dom.createTextNode(str(value))
            node.appendChild(text)

        elif type(value) == float:
            newnode.setAttribute('py_type', 'float')
            text = self.__dom.createTextNode(str(value))
            node.appendChild(text)

        elif type(value) == complex:
            newnode.setAttribute('py_type', 'complex')
            text = self.__dom.createTextNode(str(value).strip('()'))
            node.appendChild(text)

        elif type(value) == bool:
            newnode.setAttribute('py_type', 'bool')
            text = self.__dom.createTextNode(str(value))
            node.appendChild(text)

        # Lists and tuples and dictionaries (oh my!)
        # Note: this method is called recursively to process 
        # structures that contain simpler types

        elif type(value) == list:
            newnode.setAttribute('py_type', 'list')
            newnode.setAttribute('item_count', str(len(value)))
            count = 1
            for item in value:
                self.__InsertValue(node, nodeName + '-' + str(count), item)
                count += 1

        elif type(value) == tuple:
            newnode.setAttribute('py_type', 'tuple')
            newnode.setAttribute('item_count', str(len(value)))
            count = 1
            for item in value:
                self.__InsertValue(node, nodeName + '-' + str(count), item)
                count += 1

        # Note: dictionaries are converted to key,value tuple and
        # typed as dict in attribute (we will sort it out later)

        elif type(value) == dict:
            newnode.setAttribute('py_type', 'dict')
            newnode.setAttribute('item_count', str(len(value)))
            count = 1
            for item in value.items():
                self.__InsertValue(node, nodeName + '-' + str(count), item)
                count += 1
        else:
            raise XMLManagerError("UnsupportedType", str(type(value)))


    def getitem(self, namedef=''):
        """ Get the requested node(s) from DOM tree
            Parameters: 
                namedef = string representing a node path. If not given/blank,
                            text from root of XML document will be returned.
            Returns: the data as orignally typed or None if not found
        """
        # Break path into parts and move down the path until we get to
        # the parent of the desired node (hence path[0:-2])

        path = namedef.split('/')
        node = self.__FindNode(path[0:-1])

        # Get list of nodes matching end node tag

        nodelist = node.getElementsByTagName(path[-1])

        # Begin iterating through all the children of this node and
        # compile the node data into an list.  Type according to py_type
        # attribute, if attrib does not exist, type as 'str'

        temp_list = []  # initialize list
        attrib = None
        for node in nodelist:
            attrib = node.getAttribute('py_type')

        # added lstrip() and rstrip() to node text values to 
        # prevent errors reloading values from a saved file via the minidom 
        # built-in writexml().  This eliminates the need for pyxml's PrettyPrint
            if attrib == 'none':
                temp_list.append(None)
            elif attrib in ['','str']:
                temp_list.append(str((self.__NodeText(node.childNodes).lstrip()).rstrip()))
            elif attrib == 'unicode':
                temp_list.append(unicode((self.__NodeText(node.childNodes).lstrip()).rstrip()))
            elif attrib == 'int':
                temp_list.append(int((self.__NodeText(node.childNodes).lstrip()).rstrip())) 
            elif attrib == 'long':
                temp_list.append(long((self.__NodeText(node.childNodes).lstrip()).rstrip()))
            elif attrib == 'float':
                temp_list.append(float((self.__NodeText(node.childNodes).lstrip()).rstrip())) 
            elif attrib == 'complex':
                temp_list.append(complex((self.__NodeText(node.childNodes).lstrip()).rstrip()))
            elif attrib == 'bool':
                temp_list.append((self.__NodeText(node.childNodes).lstrip()).rstrip()=='True') 
            elif attrib == 'list':
                count = int(node.getAttribute('item_count'))
                y = 1
                while y <= count:
                    temp_list.append(self.getitem(namedef+'/'+path[-1]+'-'+str(y)))
                    y += 1
            elif attrib == 'tuple':
                temp_list = ()
                count = int(node.getAttribute('item_count'))
                y = 1
                while y <= count:
                    temp_list = temp_list + (self.getitem(namedef+'/'+path[-1]+'-'+str(y)),)
                    y += 1
            elif attrib == 'dict':
                temp_list = {}
                count = int(node.getAttribute('item_count'))
                y = 1
                while y <= count:
                    key, value = self.getitem(namedef+'/'+path[-1]+'-'+str(y))
                    temp_list[key] = value
                    y += 1
            else:
                print attrib, "is unknown type"
                

        # If multiple values are found, return as a list
        # otherwise, just return the single item

        if attrib != 'list' and len(temp_list) == 1:
            return temp_list[0]
        else:
            return temp_list


    def additem(self, namedef, value):
        """ Set the requested node value(s) in DOM tree
            Parameters: 
                namedef = string representing a node path.
                value = any intrinsic type Python variable, list, tuple or
                            dictionary consisting of basic Python types
            Returns: nothing
        """
        # First check to make sure DOM is initialized 

        self.__initDOM()

        # Break path into parts and move down the path until we get to
        # the parent of the desired node (hence len(path)-1).  Remove
        # empty nodes (i.e. leading & trailing slashes)

        path = namedef.split('/')
        for x in range(1,len(path)):
            if path[x-1] == '':
                del path[x-1]
        x = 0
        node = self.__dom.documentElement   # start with root doc element
        while x < len(path)-1:
            try:
                 node = self.__FindNode([path[x]], node)
            except:
                # Node doesn't exist, create it
                newnode = self.__dom.createElement(path[x])
                node = node.appendChild(newnode)
            x += 1

        # Found the parent node to insert info into
        # Now create element to hold the item

        self.__InsertValue(node, path[-1], value)


    def save(self, destination):
        """ Save XML document to disk
            Parameters: 
                destination = string representing file name
            Returns: nothing (except satisfaction ;) )
        """
        file = open(destination,"w")
        self.__dom.writexml(file, addindent='\t', newl='\n')
        file.close()
