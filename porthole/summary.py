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

class Summary(gtk.TextView):
    def __init__(self):
        gtk.TextView.__init__(self)
        self.set_wrap_mode(gtk.WRAP_WORD)
        self.set_editable(gtk.FALSE)
        self.set_cursor_visible(gtk.FALSE)
        margin = 10
        self.set_left_margin(margin); self.set_right_margin(margin)
        tagtable = self.create_tag_table()
        self.buffer = gtk.TextBuffer(tagtable)
        self.set_buffer(self.buffer)
        self.connect("motion_notify_event", self.on_mouse_motion)
        self.url_tags = []
        self.underligned_url = False

    def create_tag_table(self):
        """Define all markup tags."""
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
        """Catch when the user clicks the url"""
        if event.type == gtk.gdk.BUTTON_RELEASE:
            load_web_page(tag.get_property("name"))           

    def on_mouse_motion(self, widget, event, data = None):
        # we need to call get_pointer, or we won't get any more events
        pointer = self.window.get_pointer()
        x, y, spam = self.window.get_pointer()
        x, y = self.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, x, y)
        tags = self.get_iter_at_location(x, y).get_tags()
        if self.underligned_url:
            self.underligned_url.set_property("underline",pango.UNDERLINE_NONE)
            self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(None)
            self.underligned_url = None
        for tag in tags:
            if tag in self.url_tags:
                tag.set_property("underline",pango.UNDERLINE_SINGLE)
                self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(gtk.gdk.Cursor
                                                                 (gtk.gdk.HAND2))
                self.underligned_url = tag
        return gtk.FALSE

    def update_package_info(self, package):
        """Update the notebook of information about a selected package"""

        def append(text, tag = None):
            """Append (unicode) text to summary buffer."""
            iter = self.buffer.get_end_iter()
            buffer = self.buffer
            if tag: buffer.insert_with_tags_by_name(iter, text, tag)
            else: buffer.insert(iter, text)

        def append_url(text):
            tag = self.buffer.create_tag(text)
            tag.set_property("foreground","blue")
            tag.connect("event",self.on_url_event)
            self.url_tags.append(tag)
            append(text,tag.get_property("name"))

        def nl(): append("\n")
        
        self.buffer.set_text("", 0)
        if not package:
            # it's really a category selected!
            return
        # read it's info
        metadata = package.get_metadata()
        ebuild = package.get_latest_ebuild()
        installed = package.get_installed()
        versions = package.get_versions()
        #dprint("SUMMARY: update_package_info(); versions")
        #dprint(versions)
        # Sort the version only list: vlist
        versions = ver_sort(versions)
        #dprint("new sorted versions[]")
        #dprint(versions)

        nonmasked = package.get_versions(include_masked = False)
        props = package.get_properties()
        description = props.description
        homepages = props.get_homepages() # may be more than one
        use_flags = props.get_use_flags()
        system_use_flags = portagelib.get_portage_environ("USE")
        table=self.buffer.get_tag_table()
        for tag in self.url_tags:
            table.remove(tag)
        self.url_tags = []
        if system_use_flags:
            system_use_flags = system_use_flags.split()
        license = props.license
        slot = unicode(props.get_slot())
        # build info into buffer

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
        
        append(package.full_name, "name"); nl()
        if description:
            append(description, "description"); nl()
        if metadata and metadata.longdescription:
            nl(); append(metadata.longdescription, "description"); nl()
        for homepage in homepages: #append(homepage, "url"); nl()
            append_url(homepage)
            nl()
        nl()         # put a space between this info and the rest
        if installed:
            append("Installed versions:\n", "property")
            show_vnums(installed)
        else:
            append("Not installed", "property")
        nl()
        if versions:
            append("Available versions:\n", "property")
            show_vnums(versions)
            nl()
        nl()         # put a space between this info and the rest, again
        if use_flags:
            append("Use flags: ", "property")
            #append(", ".join(use_flags), "value")
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
            nl()
        if license:
            append("License: ", "property"); append(license, "value"); nl()
        #if slot:
        #    append("Slot: ", "property"); append(slot, "value"); nl()
