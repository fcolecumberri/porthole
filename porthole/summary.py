#!/usr/bin/env python

'''
    Porthole Summary Class
    Loads package info into a textview and makes it pretty

    Copyright (C) 2003 - 2004 Fredrik Arnerup and Daniel G. Taylor

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

import gtk, pango
import portagelib
import string, re
from utils import load_web_page, dprint
from version_sort import ver_sort
from gettext import gettext as _

class Summary(gtk.TextView):
    """ Class to manage display and contents of package info tab """
    def __init__(self):
        """ Initialize object """
        gtk.TextView.__init__(self)
        self.set_wrap_mode(gtk.WRAP_WORD)
        self.set_editable(gtk.FALSE)
        self.set_cursor_visible(gtk.FALSE)
        margin = 10
        self.set_left_margin(margin)
        self.set_right_margin(margin)
        tagtable = self.create_tag_table()
        self.buffer = gtk.TextBuffer(tagtable)
        self.set_buffer(self.buffer)

        # Capture any mouse motion in this tab so we
        # can highlight URL links & change mouse pointer
        self.connect("motion_notify_event", self.on_mouse_motion)

        # List of active URLs in the tab
        self.url_tags = []
        self.underlined_url = False

    def create_tag_table(self):
        """ Define all markup tags """
        def create(descs):
            table = gtk.TextTagTable()
            for name, properties in descs.items():
                tag = gtk.TextTag(name); table.add(tag)
                for property, value in properties.items():
                    tag.set_property(property, value)
            return table

        table = create(
            {'name': ({'weight': pango.WEIGHT_BOLD,
                       'scale': pango.SCALE_X_LARGE,
                       'pixels-above-lines': 5}),
             'description': ({"style": pango.STYLE_ITALIC}),
             'url': ({'foreground': 'blue'}),
             'property': ({'weight': pango.WEIGHT_BOLD}),
             'value': ({}),
             'useset': ({'foreground':'darkgreen'}),
             'useunset':({'foreground':'red'}),
             'masked': ({"style": pango.STYLE_ITALIC}),
             })
        return table

    def on_url_event(self, tag, widget, event, iter):
        """ Catch when the user clicks the URL """
        if event.type == gtk.gdk.BUTTON_RELEASE:
            load_web_page(tag.get_property("name"))

    def on_mouse_motion(self, widget, event, data = None):
        # we need to call get_pointer, or we won't get any more events
        pointer = self.window.get_pointer()
        x, y, spam = self.window.get_pointer()
        x, y = self.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, x, y)
        tags = self.get_iter_at_location(x, y).get_tags()
        if self.underlined_url:
            self.underlined_url.set_property("underline",pango.UNDERLINE_NONE)
            self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(None)
            self.underlined_url = None
        for tag in tags:
            if tag in self.url_tags:
                tag.set_property("underline",pango.UNDERLINE_SINGLE)
                self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(gtk.gdk.Cursor
                                                                 (gtk.gdk.HAND2))
                self.underlined_url = tag
        return gtk.FALSE

    def update_package_info(self, package):
        """ Update the notebook of information about a selected package """

        ######################################
        # Begin supporting internal functions

        def append(text, tag = None):
            """ Append (unicode) text to summary buffer """
            iter = self.buffer.get_end_iter()
            buffer = self.buffer
            if tag: buffer.insert_with_tags_by_name(iter, text, tag)
            else: buffer.insert(iter, text)

        def append_url(text):
            """ Append URL to textbuffer and connect an event """
            tag = self.buffer.create_tag(text)
            tag.set_property("foreground","blue")
            tag.connect("event", self.on_url_event)
            self.url_tags.append(tag)
            append(text, tag.get_property("name"))

        def nl(x=1):
            """ Append a x new lines to the buffer """ 
            append("\n"*x)

        def show_vnums(ebuilds):
            spam = []
            oldslot = -1
            for ebuild in ebuilds:
                version = portagelib.get_version(ebuild)
                slot = portagelib.get_property(ebuild, "SLOT")
                if not slot == oldslot:
                   if spam:
                      append(", ".join(spam), "value")
                      nl()
                      spam = []
                   append("\tSlot %s: " % slot, "property")
                   oldslot = slot
                if ebuild not in nonmasked:
                    version = "(" + version + ")"
                spam += [version]
            append(", ".join(spam), "value")
            return

        # End supporting internal functions
        ####################################


        # build info into buffer
        self.buffer.set_text("", 0)
        if not package:
            # Category is selected, just exit
            return

        # Get the package info
	#dprint("SUMMARY: get package info")
        metadata = package.get_metadata()
        ebuild = package.get_latest_ebuild()
        installed = package.get_installed()
        versions = package.get_versions()
        nonmasked = package.get_versions(include_masked = False)
        props = package.get_properties()
        description = props.description
        homepages = props.get_homepages() # may be more than one
	#dprint("SUMMARY: Summary; getting use flags")
        use_flags = props.get_use_flags()
        license = props.license
        slot = unicode(props.get_slot())

        # Sort the versions in release order
        versions = ver_sort(versions)

        # Get the tag table and remove all URL tags
        table=self.buffer.get_tag_table()
        for tag in self.url_tags:
            table.remove(tag)
        self.url_tags = []

        # Turn system use flags into a list
        system_use_flags = portagelib.get_portage_environ("USE")
        if system_use_flags:
            system_use_flags = system_use_flags.split()
	    #dprint("SUMMARY: system_use_flags = "+str(system_use_flags))

        #############################
        # Begin adding text to tab
        #############################
        
        # Full package name
        append(package.full_name, "name")
        nl()
        
        # Description, if available
        if description:
            append(description, "description")
            nl()

        # Metadata long description(s), if available
        if metadata and metadata.longdescription:
            append(metadata.longdescription, "description")
            nl()
        nl()

        # Insert homepage(s), if any
        x = 0
        if homepages:
            for homepage in homepages:
                if x > 0:
                    append( ', ')
                append_url(homepage)
                x += 1
            nl(2)
    
        # Installed version(s)
        if installed:
            append(_("Installed versions:\n"), "property")
            show_vnums(installed)
            nl()
        else:
            append(_("Not installed"), "property")
            nl()

        # Remaining versions
        if versions:
            append(_("Available versions:\n"), "property")
            show_vnums(versions)
            nl(2)        

        # Use flags
        if use_flags:
            append(_("Use flags: "), "property")
            first_flag = True
            for flag in use_flags:
                if not first_flag:
                    append(", ", "value")
                else:
                    first_flag = False
                # Added +/- for color impaired folks
                if flag in system_use_flags:
                    append('+' + flag,"useset")
                else:
                    append('-' + flag,"useunset")
            nl(2)

        # License
        if license:
            append(_("License: "), "property")
            append(license, "value")
            nl()
