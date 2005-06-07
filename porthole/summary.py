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
from utils import dprint
from loaders import load_web_page
from version_sort import ver_sort
from gettext import gettext as _

class Summary(gtk.TextView):
    """ Class to manage display and contents of package info tab """
    def __init__(self, prefs):
        """ Initialize object """
        gtk.TextView.__init__(self)
        self.prefs = prefs
        self.set_wrap_mode(gtk.WRAP_WORD)
        self.set_editable(False)
        self.set_cursor_visible(False)
        margin = 10
        self.set_left_margin(margin)
        self.set_right_margin(margin)
        tagtable = self.create_tag_table()
        self.buffer = gtk.TextBuffer(tagtable)
        self.set_buffer(self.buffer)
        self.license_dir = "file://"+ portagelib.portdir + "/licenses/"

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
        return False

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

        def append_url(text, url, colour):
            """ Append URL to textbuffer and connect an event """
            tag = self.buffer.create_tag(url)
            tag.set_property("foreground", colour)
            tag.connect("event", self.on_url_event)
            self.url_tags.append(tag)
            append(text, tag.get_property("name"))

        def nl(x=1):
            """ Append a x new lines to the buffer """ 
            append("\n"*x)

        def show_vnums(ebuilds):
            spam = []
            oldslot = -1
            first_ebuild = True
            for ebuild in ebuilds:
                # set the tag to the default
                tag = "value" 
                version = portagelib.get_version(ebuild)
                if ebuild in versions:   # annoying message is output by portage if it isn't
                    slot = portagelib.get_property(ebuild, "SLOT")
                else:
                    slot = "?"  # someone removed the ebuild for our installed package. Damn them!
                if not slot == oldslot:
                   if spam:
                      #append(", ".join(spam), "value")
                      nl()
                      spam = []
                   append("\tSlot %s: " % slot, "property")
                   oldslot = slot
                   first_ebuild = True

                if not first_ebuild:
                    append(", ", "value")

                if ebuild not in nonmasked:
                    if ebuild in hardmasked:
                        version = "![" + version + "]"
                        # set the tag to highlight this version
                        tag = "useunset" # fixme:  need to make this user settable and different from use flags
                    else:
                        version = "~(" + version + ")"
                        # set the tag to highlight this version
                        tag = "useset" # fixme:  need to make this user settable and different from use flags
                append(version, tag)
                first_ebuild = False
                spam += [version]  # now only used to track the need for a new slot
            #append(", ".join(spam), "value")
            return
        
        def create_ebuild_table(ebuilds):
            archlist = ["alpha", "amd64", "arm", "hppa", "ia64", "mips", "ppc",
                       "ppc64", "ppc-macos", "s390", "sparc", "x86"]
            myarch = portagelib.get_arch()
            if self.prefs.advemerge.enable_all_keywords:
            #if True:    # Just for testing, until we have a preferences dialog.
                rows = 1 + len(ebuilds)
                cols = 1 + len(archlist)
                table = gtk.Table(rows, cols)
                table.attach(boxify(gtk.Label(), "white"), 0, 1, 0, 1)
                x = 0
                for arch in archlist:
                    x += 1
                    label = gtk.Label(arch)
                    label.set_padding(3, 3)
                    table.attach(boxify(label, "#EEEEEE"), x, x+1, 0, 1)
                y = len(ebuilds) + 1
                for ebuild in ebuilds:
                    y -= 1
                    version = portagelib.get_version(ebuild)
                    label = gtk.Label(str(version))
                    label.set_padding(3, 3)
                    table.attach(boxify(label, "#EEEEEE"), 0, 1, y, y+1)
                    keys = package.get_properties(ebuild).get_keywords()
                    x = 0
                    for arch in archlist:
                        x += 1
                        if "".join(["~", arch]) in keys:
                            text = "~"
                            color = "#EEEE90"
                        elif arch in keys:
                            text = "+"
                            color = "#90EE90"
                        else:
                            text = "-"
                            color = "#EEEEEE"
                        if ebuild in hardmasked and text != "-":
                            text = "".join(["M", text])
                            color = "#ED9191"
                        if ebuild in installed and arch == myarch:
                            color = "#9090EE"
                        label = gtk.Label(text)
                        table.attach(boxify(label, color), x, x+1, y, y+1)
            else:
                rows = 2
                cols = 1 + len(ebuilds)
                table = gtk.Table(rows, cols)
                label = gtk.Label()
                table.attach(boxify(label, "white"), 0, 1, 0, 1)
                label = gtk.Label(myarch)
                label.set_padding(3, 3)
                table.attach(boxify(label, "#EEEEEE"), 0, 1, 1, 2)
                x = 0
                for ebuild in ebuilds:
                    x += 1
                    version = portagelib.get_version(ebuild)
                    label = gtk.Label(str(version))
                    label.set_padding(3, 3)
                    table.attach(boxify(label, "#EEEEEE"), x, x+1, 0, 1)
                    keys = package.get_properties(ebuild).get_keywords()
                    if "".join(["~", myarch]) in keys:
                        text = "~"
                        color = "#EEEE90"
                    elif myarch in keys:
                        text = "+"
                        color = "#90EE90"
                    else:
                        text = "-"
                        color = "#EEEEEE"
                    if ebuild in hardmasked and text != "-":
                        text = "".join(["M", text])
                        color = "#ED9191"
                    if ebuild in installed:
                        color = "#9090EE"
                    label = gtk.Label(text)
                    table.attach(boxify(label, color), x, x+1, 1, 2)
            table.set_row_spacings(1)
            table.set_col_spacings(1)
            table.set_border_width(1)
            tablebox = boxify(table, "darkgrey")
            tablebox.show_all()
            iter = self.buffer.get_end_iter()
            anchor = self.buffer.create_child_anchor(iter)
            self.add_child_at_anchor(tablebox, anchor)
            nl()
            nl()
            
        def boxify(label, color = None):
            box = gtk.EventBox()
            box.add(label)
            if color:
                style = box.get_style().copy()
                style.bg[gtk.STATE_NORMAL] = gtk.gdk.color_parse(color)
                box.set_style(style)
            return box
        
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
        installed = package.get_installed()
        versions = package.get_versions()
        nonmasked = package.get_versions(include_masked = False)
        
        # added by Tommy
        hardmasked = package.get_hard_masked()

        best = portagelib.best(installed + nonmasked)
        #dprint("SUMMARY: best = %s" %best)
        if best == "": # all versions are masked and the package is not installed
            ebuild = package.get_latest_ebuild(True) # get latest masked version
        else:
            ebuild = best
        #dprint("SUMMARY: getting properties for ebuild version %s" %ebuild)
        props = package.get_properties(ebuild)
        description = props.description
        homepages = props.get_homepages() # may be more than one
        #dprint("SUMMARY: Summary; getting use flags")
        use_flags = props.get_use_flags()
        keywords = props.get_keywords()
        licenses = props.license
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
            nl(2)

        # Metadata long description(s), if available
        if metadata and metadata.longdescription:
            append("Long Description: ", "property")
            append(metadata.longdescription, "description")
            nl()
        nl()

        # Insert homepage(s), if any
        x = 0
        if homepages:
            for homepage in homepages:
                if x > 0:
                    append( ', ')
                append_url(homepage, homepage, "blue")
                x += 1
            nl(2)
        
        # display a table of architectures and support / stability
        # like on packages.gentoo.org :)
        create_ebuild_table(versions)
        
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

        append("Properties for version: ", "property")
        append(portagelib.get_version(ebuild))
        nl()

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

        # Keywords
        if keywords:
            append(_("Keywords: "), "property")
            first_keyword = True
            for keyword in keywords:
                if not first_keyword:
                    append(", ", "value")
                else:
                    first_keyword = False
                append(keyword, "value")
            nl(2)

        # License
        if licenses:
            append(_("License: "), "property")
            _licenses = licenses.split()
            x = 0
            for license in _licenses:
                if license not in ["||","(",")"]:
                    if x > 0:
                        append( ', ')
                    append_url(license, self.license_dir + license, "blue")
                    x += 1
            nl()
