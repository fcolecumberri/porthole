#!/usr/bin/env python

'''
    Porthole Summary Class
    Loads package info into a textview and makes it pretty

    Copyright (C) 2003 - 2006 Fredrik Arnerup, Daniel G. Taylor,
    Brian Dolbec, Tommy Iorns

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
import re
from types import *
import utils.debug
from utils import utils

import backends
portage_lib = backends.portage_lib

import db
import config

from backends.version_sort import ver_sort
from backends.utilities import reduce_flags
from loaders.loaders import load_web_page
from gettext import gettext as _

class Summary(gtk.TextView):
    """ Class to manage display and contents of package info tab """
    def __init__(self, dispatcher, re_init_portage):
        """ Initialize object """
        gtk.TextView.__init__(self)
        self.re_init_portage = re_init_portage
        # get the preferences we need
        self.enable_archlist = config.Prefs.globals.enable_archlist
        self.archlist = config.Prefs.globals.archlist
        self.dispatch = dispatcher
        self.myarch = portage_lib.get_arch()
        self.tooltips = gtk.Tooltips()
        self.set_wrap_mode(gtk.WRAP_WORD)
        self.set_editable(False)
        self.set_cursor_visible(False)
        margin = 10
        self.set_left_margin(margin)
        self.set_right_margin(margin)
        tagtable = self.create_tag_table()
        self.buffer = gtk.TextBuffer(tagtable)
        self.set_buffer(self.buffer)
        self.license_dir = "file://"+ portage_lib.portdir + "/licenses/"
        self.package = None
        self.ebuild = None
        self.config_types = db.userconfigs.get_types()

        # Capture any mouse motion in this tab so we
        # can highlight URL links & change mouse pointer
        self.connect("motion_notify_event", self.on_mouse_motion)

        # List of active URLs in the tab
        self.url_tags = []
        self.underlined_url = False
        self.reset_cursor = 'Please'
        
        # create popup menu for rmb-click
        arch = "~" + portage_lib.get_arch()
        menu = gtk.Menu()
        menuitems = {}
        menuitems["emerge"] = gtk.MenuItem(_("Emerge this ebuild"))
        menuitems["emerge"].connect("activate", self.emerge)
        menuitems["pretend-emerge"] = gtk.MenuItem(_("Pretend Emerge this ebuild"))
        menuitems["pretend-emerge"].connect("activate", self.emerge, True, None)
        menuitems["sudo-emerge"] = gtk.MenuItem(_("Sudo Emerge this ebuild"))
        menuitems["sudo-emerge"].connect("activate", self.emerge, None, True)
        menuitems["unmerge"] = gtk.MenuItem(_("Unmerge this ebuild"))
        menuitems["unmerge"].connect("activate", self.unmerge)
        menuitems["sudo-unmerge"] = gtk.MenuItem(_("Sudo Unmerge this ebuild"))
        menuitems["sudo-unmerge"].connect("activate", self.unmerge, True)
        menuitems["add-ebuild-keyword"] = gtk.MenuItem(_("Add %s to package.keywords (for this ebuild only)") % arch)
        menuitems["add-ebuild-keyword"].connect("activate", self.add_keyword_ebuild)
        menuitems["add-keyword"] = gtk.MenuItem(_("Add %s to package.keywords") % arch)
        menuitems["add-keyword"].connect("activate", self.add_keyword)
        menuitems["remove-keyword"] = gtk.MenuItem(_("Remove %s from package.keywords") % arch)
        menuitems["remove-keyword"].connect("activate", self.remove_keyword)
        menuitems["package-unmask"] = gtk.MenuItem(_("Unmask this ebuild"))
        menuitems["package-unmask"].connect("activate", self.package_unmask)
        menuitems["un-package-unmask"] = gtk.MenuItem(_("Remask this ebuild"))
        menuitems["un-package-unmask"].connect("activate", self.un_package_unmask)
        menuitems["show_props"] = gtk.MenuItem(_("Show the propeties for this ebuild"))
        menuitems["show_props"].connect("activate", self.show_version)
        
        for item in menuitems.values():
            menu.append(item)
            item.show()
        
        self.popup_menu = menu
        self.popup_menuitems = menuitems
        self.dopopup = None
        self.selected_ebuild = None
        self.selected_arch = None
        self.connect("button_press_event", self.on_button_press)

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
        if self.reset_cursor: # defaults to gtk.gdk.XTERM - reset it to None
            self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(None)
            self.reset_cursor = False
        return False

    def update_package_info(self, package, _ebuild = None):
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
            """ Append x new lines to the buffer """ 
            append("\n"*x)

        def show_vnums(ebuilds, show_all=False):
            spam = []
            oldslot = -1
            first_ebuild = True
            for ebuild in ebuilds:
                # set the tag to the default
                tag = "value" 
                version = portage_lib.get_version(ebuild)
                keys = package.get_properties(ebuild).get_keywords()
                if not show_all and self.myarch not in keys and ''.join(['~',self.myarch]) not in keys:
                    # we won't display the ebuild if it's not available to us
                    continue
                slot = portage_lib.get_property(ebuild, "SLOT")
                if not slot == oldslot:
                    if spam:
                        #append(", ".join(spam), "value")
                        nl()
                        spam = []
                    if slot != '0':
                        append(_("\tSlot %s: ") % slot, "property")
                    else: append("\t", "property")
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
            if first_ebuild: # only still true if no ebuilds were acceptable
                append(_('\tNone'), 'value')
            #append(", ".join(spam), "value")
            return
        
        def create_ebuild_table(versions):
            myarch = self.myarch
            ebuilds = versions[:] # make a copy
            modified = False
            for entry in installed:
                if entry not in ebuilds:
                    utils.debug.dprint("SUMMARY; create_ebuild_table(): adding %s to ebuild list" % entry)
                    ebuilds.append(entry)
                    modified = True
            if modified: ebuilds = ver_sort(ebuilds) # otherwise already sorted
            
            if config.Prefs.globals.enable_archlist:
                archlist = config.Prefs.globals.archlist
                utils.debug.dprint("SUMMARY: create_ebuild_table: creating archlist enabled table for: " + str(archlist))
            else:
                archlist = [myarch]
                utils.debug.dprint("SUMMARY: create_ebuild_table: creating single arch table for: " + str(archlist))
            #if True: # saves an unindent for testing change    
            rows = 1 + len(ebuilds)
            cols = 3 + len(archlist)
            table = gtk.Table(rows, cols)
            table.attach(boxify(gtk.Label(), "white"), 0, 1, 0, 1)
            label = gtk.Label(_("Slot"))
            label.set_padding(3, 3)
            table.attach(boxify(label, "#EEEEEE"), 1, 2, 0, 1)
            label = gtk.Label(_("Overlay"))
            label.set_padding(3, 3)
            table.attach(boxify(label, "#EEEEEE"), 2, 3, 0, 1)
            x = 2
            for arch in archlist:
                utils.debug.dprint("SUMMARY: create_ebuild_table: arch is: " + str(arch))
                x += 1
                label = gtk.Label(arch)
                label.set_padding(3, 3)
                table.attach(boxify(label, "#EEEEEE"), x, x+1, 0, 1)
            y = rows
            for ebuild in ebuilds:
                y -= 1
                version = portage_lib.get_version(ebuild)
                ver_label = gtk.Label(str(version))
                ver_label.set_padding(3, 3)
                # slot column
                slot =  package.get_properties(ebuild).get_slot()
                slot_label = gtk.Label(str(slot))
                slot_label.set_padding(3, 3)
                # overlay column
                overlay = portage_lib.get_overlay(ebuild)
                if type(overlay) is IntType: # catch obsolete 
                    overlay = _("Ebuild version no longer supported")
                    overlay_label = gtk.Label(_("Obsolete"))
                    label_color = "#ED9191"
                else:
                    if overlay != portage_lib.portdir:
                        overlay_label = gtk.Label(_("Y"))
                    else:
                        overlay_label = gtk.Label(_("N"))
                    label_color = "#EEEEEE"
                overlay_label.set_padding(3, 3)
                box = boxify(overlay_label, label_color)
                self.tooltips.set_tip(box, overlay)
                # attach version, slot and overlay columns
                table.attach(boxify(ver_label, label_color, ebuild, '.', "version"), 0, 1, y, y+1)
                table.attach(boxify(slot_label, label_color), 1, 2, y, y+1)
                table.attach(box, 2, 3, y, y+1)
                
                keys = package.get_properties(ebuild).get_keywords()
                x = 2
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
                    #utils.debug.dprint("SUMMARY: create_ebuild_table(); keyword_unmasked[ebuild] = " + str(keyword_unmasked[ebuild]))
                    if (ebuild in keyword_unmasked and '~' in text and
                                ('~' + arch in keyword_unmasked[ebuild] or keyword_unmasked[ebuild] == [] )):
                        # take account of package.keywords in text but leave colour unchanged
                        text = text.replace('~', '(+)')
                    if ebuild in package_unmasked and 'M' in text:
                        text = '[' + text.replace('M', '') + ']'
                    label = gtk.Label(text)
                    box = boxify(label, color=color, ebuild=ebuild, arch=arch, text=text)
                    if "M" in text or "[" in text:
                        self.tooltips.set_tip(box, portage_lib.get_masking_reason(ebuild))
                    table.attach(box, x, x+1, y, y+1)
            table.set_row_spacings(1)
            table.set_col_spacings(1)
            table.set_border_width(1)
            tablebox = boxify(table, "darkgrey")
            tablebox.show_all()
            iter = self.buffer.get_end_iter()
            anchor = self.buffer.create_child_anchor(iter)
            self.add_child_at_anchor(tablebox, anchor)
            nl(2)
            
        def boxify(label, color=None, ebuild=None, arch=None, text=None):
            box = gtk.EventBox()
            box.add(label)
            if color:
                style = box.get_style().copy()
                style.bg[gtk.STATE_NORMAL] = gtk.gdk.color_parse(color)
                box.set_style(style)
            if ebuild:
                box.color = color
                box.ebuild = ebuild
                box.arch = arch
                box.text = text
                box.connect("button-press-event", self.on_table_clicked)
                box.connect("enter-notify-event", self.on_table_mouse)
                box.connect("leave-notify-event", self.on_table_mouse)
            return box

        def show_props(ebuild):
            # Check package.use to see if it applies to this ebuild at all
            package_use_flags = db.userconfigs.get_user_config('USE', ebuild=ebuild)
            #package_use_flags = db.userconfigs.get_useflags(ebuild)
            utils.debug.dprint("SUMARY: update_package_info(); package_use_flags = %s" %str(package_use_flags))
            if package_use_flags != None and package_use_flags != []:
                utils.debug.dprint("SUMARY: update_package_info(); adding package_use_flags to ebuild_use_flags")
                ebuild_use_flags = reduce_flags(system_use_flags + package_use_flags)
            else:
                utils.debug.dprint("SUMARY: update_package_info(); adding only system_use_flags to ebuild_use_flags")
                ebuild_use_flags = system_use_flags
            # Use flags
            if use_flags and config.Prefs.summary.showuseflags:
                append(_("Use flags: "), "property")
                first_flag = True
                for flag in use_flags:
                    ## this next commented out block is due to the new reduce_flags function, so it is no longer needed
                    # Check to see if flag applies:
                    #if flag in ebuild_use_flags and '-' + flag in ebuild_use_flags:
                        # check to see which comes last (this will be the applicable one)
                        #ebuild_use_flags.reverse()  # no longer needed
                        #if ebuild_use_flags.index(flag) # < ebuild_use_flags.index('-' + flag):
                        #    flag_active = True
                        #else: # ebuild_use_flags.index('-' + flag):
                        #    flag_active = False
                        #ebuild_use_flags.reverse()
                    if flag in ebuild_use_flags:
                        flag_active = True
                    else:
                        flag_active = False
                    
                    if not first_flag:
                        append(", ", "value")
                    else:
                        first_flag = False
                    # Added +/- for color impaired folks
                    if flag_active:
                        append('+' + flag,"useset")
                    else:
                        append('-' + flag,"useunset")
                nl(2)

            # Keywords
            if keywords and config.Prefs.summary.showkeywords:
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
            if licenses and config.Prefs.summary.showlicense:
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
        
        def show_configs(ebuild):
            append(_("User Configs: "), "property")
            nl()
            for type in self.config_types:
                append('\t' + type + ': ', "property")
                config_atoms = db.userconfigs.get_atom(type, None, ebuild)
                if len(config_atoms):
                    line = 0
                    for atom in config_atoms:
                        if line > 0:
                            append('\t\t\t   ', "property")
                        append(str(atom), "value")
                        nl()
                        line += 1
                else:
                    append(_("None"))
                    nl()

        # End supporting internal functions
        ####################################


        # build info into buffer
        self.buffer.set_text("", 0)
        if not package:
            # Category is selected, just exit
            return
        
        self.package = package
        
        # Get the package info
        #utils.debug.dprint("SUMMARY: get package info")
        metadata = package.get_metadata()
        installed = self.installed = package.get_installed()
        utils.debug.dprint("SUMMARY: installed = %s" %str(installed))
        versions = package.get_versions()
        nonmasked = package.get_versions(include_masked = False)
        utils.debug.dprint("SUMMARY: nonmasked = %s" %str(nonmasked))
        
        # added by Tommy
        hardmasked = package.get_hard_masked()
        #keyword_unmasked = portage_lib.get_keyword_unmasked_ebuilds(
        #                    archlist=self.archlist, full_name=package.full_name)
        utils.debug.dprint("SUMMARY: get package info, name = " + package.full_name)
        keyword_unmasked = db.userconfigs.get_user_config('KEYWORDS', name=package.full_name)
        package_unmasked = db.userconfigs.get_user_config('UNMASK', name=package.full_name)
        
        best = portage_lib.best(installed + nonmasked)
        #utils.debug.dprint("SUMMARY: best = %s" %best)
        if _ebuild:
            self.ebuild = _ebuild
        else:
            if best == "": # all versions are masked and the package is not installed
                self.ebuild = package.get_latest_ebuild(True) # get latest masked version
            else:
                self.ebuild = best
        #utils.debug.dprint("SUMMARY: getting properties for ebuild version %s" %ebuild)
        props = package.get_properties(self.ebuild)
        description = props.description
        homepages = props.get_homepages() # may be more than one
        #utils.debug.dprint("SUMMARY: Summary; getting use flags")
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
        system_use_flags = portage_lib.get_portage_environ("USE")
        if system_use_flags:
            system_use_flags = system_use_flags.split()
            #utils.debug.dprint("SUMMARY: system_use_flags = "+str(system_use_flags))

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
        if metadata and metadata.longdescription and config.Prefs.summary.showlongdesc:
            append(_("Long Description: "), "property")
            append(metadata.longdescription, "description")
            nl(2)
        
        # Insert homepage(s), if any
        x = 0
        if homepages and config.Prefs.summary.showurl:
            for homepage in homepages:
                if x > 0:
                    append( ', ')
                append_url(homepage, homepage, "blue")
                x += 1
            nl(2)
        
        # display a table of architectures and support / stability
        # like on packages.gentoo.org :)
        if config.Prefs.summary.showtable: create_ebuild_table(versions)
        
        # Installed version(s)
        if config.Prefs.summary.showinstalled:
            if installed:
                append(_("Installed versions:\n"), "property")
                show_vnums(installed, show_all=True)
                nl(2)
            else:
                append(_("Not installed"), "property")
                nl(2)
        
        # Remaining versions
        if versions and config.Prefs.summary.showavailable:
            append(_("Available versions for %s:\n") % self.myarch, "property")
            show_vnums(versions)
            nl(2)
        
        append(_("Properties for version: "), "property")
        append(portage_lib.get_version(self.ebuild))
        nl(2)
        show_props(self.ebuild)
        nl()
        show_configs(self.ebuild)

    def on_button_press(self, summaryview, event):
        """Button press callback for Summary.
        (note: table clicks are handled in on_table_clicked)"""
        utils.debug.dprint("SUMMARY: Handling SummaryView button press event")
        if event.type != gtk.gdk.BUTTON_PRESS:
            utils.debug.dprint("SUMMARY: Strange event type got passed to on_button_press() callback...")
            utils.debug.dprint(event.type)
        if event.button == 3: # secondary mouse button
            return self.do_popup()
        else: return False
    
    def do_popup(self):
        utils.debug.dprint("SUMMARY: do_popup(): pop!")
        return False
    
    def on_table_clicked(self, eventbox, event):
        utils.debug.dprint("SUMMARY: EventBox clicked, button = " + str(event.button))
        #utils.debug.dprint(eventbox)
        #utils.debug.dprint(eventbox.get_parent())
        utils.debug.dprint([eventbox.ebuild, eventbox.arch, eventbox.text])
        if event.button == 1 and eventbox.text == 'version': # left click
            self.selected_ebuild = eventbox.ebuild
            self.show_version(None)
        if event.button == 3: # secondary mouse button
            self.do_table_popup(eventbox, event)
        return True
    
    def do_table_popup(self, eventbox, event):
        self.selected_ebuild = eventbox.ebuild
        self.selected_arch = eventbox.arch
        # moved these from is_root bit as we can sudo them now
        if utils.is_root() or utils.can_gksu():
            if '~' in eventbox.text:
                self.popup_menuitems["add-keyword"].show()
            else: self.popup_menuitems["add-keyword"].hide()
            if '(+)' in eventbox.text:
                self.popup_menuitems["remove-keyword"].show()
            else: self.popup_menuitems["remove-keyword"].hide()
            if 'M' in eventbox.text:
                self.popup_menuitems["package-unmask"].show()
            else: self.popup_menuitems["package-unmask"].hide()
            if '[' in eventbox.text:
                self.popup_menuitems["un-package-unmask"].show()
            else: self.popup_menuitems["un-package-unmask"].hide()
        else:
            self.popup_menuitems["add-keyword"].hide()
            self.popup_menuitems["remove-keyword"].hide()
            self.popup_menuitems["package-unmask"].hide()
            self.popup_menuitems["un-package-unmask"].hide()
        if utils.is_root():
            #if '~' in eventbox.text:
            #    self.popup_menuitems["add-keyword"].show()
            #else: self.popup_menuitems["add-keyword"].hide()
            #if '(+)' in eventbox.text:
            #    self.popup_menuitems["remove-keyword"].show()
            #else: self.popup_menuitems["remove-keyword"].hide()
            #if 'M' in eventbox.text:
            #    self.popup_menuitems["package-unmask"].show()
            #else: self.popup_menuitems["package-unmask"].hide()
            #if '[' in eventbox.text:
            #    self.popup_menuitems["un-package-unmask"].show()
            #else: self.popup_menuitems["un-package-unmask"].hide()
            if eventbox.ebuild in self.installed:
                self.popup_menuitems["unmerge"].show()
                self.popup_menuitems["emerge"].hide()
                self.popup_menuitems["pretend-emerge"].hide()
            else:
                self.popup_menuitems["unmerge"].hide()
                self.popup_menuitems["emerge"].show()
                self.popup_menuitems["pretend-emerge"].show()
            self.popup_menuitems["sudo-emerge"].hide()
            self.popup_menuitems["sudo-unmerge"].hide()
        else:
            self.popup_menuitems["emerge"].hide()
            self.popup_menuitems["unmerge"].hide()
            #self.popup_menuitems["add-keyword"].hide()
            #self.popup_menuitems["remove-keyword"].hide()
            #self.popup_menuitems["package-unmask"].hide()
            #self.popup_menuitems["un-package-unmask"].hide()
            if eventbox.ebuild in self.installed:
                if utils.can_sudo():
                    self.popup_menuitems["sudo-unmerge"].show()
                else:
                    self.popup_menuitems["sudo-unmerge"].hide()
                self.popup_menuitems["sudo-emerge"].hide()
                self.popup_menuitems["pretend-emerge"].hide()
            else:
                self.popup_menuitems["sudo-unmerge"].hide()
                if utils.can_sudo():
                    self.popup_menuitems["sudo-emerge"].show()
                else:
                    self.popup_menuitems["sudo-emerge"].hide()
                self.popup_menuitems["pretend-emerge"].show()
        self.popup_menu.popup(None, None, None, event.button, event.time)
        # de-select the table cell. Would be nice to leave it selected,
        # but it doesn't get de-selected when the menu is closed.
        eventbox.emit("leave-notify-event", gtk.gdk.Event(gtk.gdk.LEAVE_NOTIFY))
        return True
    
    def on_table_mouse(self, eventbox, event):
        if event.mode != gtk.gdk.CROSSING_NORMAL: return False
        if event.type == gtk.gdk.ENTER_NOTIFY:
            #utils.debug.dprint("SUMMARY: on_table_mouse(): Enter notify")
            # note: colour should be of form "#xxxxxx" (not name)
            if eventbox.color.startswith('#'):
                colour = eventbox.color[1:]
                colourlist = ['#']
                # make mouseover'd box twice as bright
                for char in colour:
                    # not very technical
                    colourint = int('0x' + char, 0)
                    newint = (colourint + 16) / 2
                    tempchar = hex(newint)[2]
                    colourlist.append(tempchar)
                newcolour = ''.join(colourlist)
                #utils.debug.dprint("old colour = %s" % eventbox.color)
                #utils.debug.dprint("new colour = %s" % newcolour)
                style = eventbox.get_style().copy()
                style.bg[gtk.STATE_NORMAL] = gtk.gdk.color_parse(newcolour)
                eventbox.set_style(style)
        elif event.type == gtk.gdk.LEAVE_NOTIFY:
            #utils.debug.dprint("SUMMARY: on_table_mouse(): Leave notify")
            style = eventbox.get_style().copy()
            style.bg[gtk.STATE_NORMAL] = gtk.gdk.color_parse(eventbox.color)
            eventbox.set_style(style)
        return False
    
    def emerge(self, menuitem_widget, pretend=None, sudo=None):
        emergestring = 'emerge'
        if pretend:
            emergestring += ' pretend'
        if sudo:
            emergestring += ' sudo'
        self.dispatch(emergestring, self.selected_ebuild)
        
    def unmerge(self, menuitem_widget, sudo=None):
        if sudo:
            self.dispatch("unmerge sudo", self.selected_ebuild)
        else:
            self.dispatch("unmerge", self.selected_ebuild)
    
    def update_callback(self):
        # reset package info
        self.package.best_ebuild = None
        self.package.latest_ebuild = None
        # reload view
        self.update_package_info(self.package)
        self.re_init_portage()
    
    def add_keyword_ebuild(self, menuitem_widget):
        arch = "~" + portage_lib.get_arch()
        ebuild = self.selected_ebuild
        db.userconfigs.set_user_config('KEYWORDS', ebuild=ebuild, add=arch, callback=self.update_callback)

    def add_keyword(self, widget):
        arch = "~" + portage_lib.get_arch()
        name = self.package.full_name
        string = name + " " + arch + "\n"
        utils.debug.dprint("Summary: Package view add_keyword(); %s" %string)
        db.userconfigs.set_user_config('KEYWORDS', name=name, add=arch, callback=self.update_callback)

    def remove_keyword_ebuild(self, menuitem_widget):
        arch = "~" + portage_lib.get_arch()
        ebuild = self.selected_ebuild
        db.userconfigs.set_user_config('KEYWORDS', ebuild=ebuild, remove=arch, callback=self.update_callback)

    def remove_keyword(self, menuitem_widget):
        arch = "~" + portage_lib.get_arch()
        name = self.package.full_name
        string = name + " " + arch + "\n"
        utils.debug.dprint("Summary: Package view remove_keyword(); %s" %string)
        db.userconfigs.set_user_config('KEYWORDS', name=name, remove=arch, callback=self.update_callback)
    
    def package_unmask(self, menuitem_widget):
        ebuild = "=" + self.selected_ebuild
        db.userconfigs.set_user_config('UNMASK', add=ebuild, callback=self.update_callback)
    
    def un_package_unmask(self, menuitem_widget):
        ebuild = "=" + self.selected_ebuild
        db.userconfigs.set_user_config('UNMASK', remove=ebuild, callback=self.update_callback)
    
    def show_version(self, menuitem_widget):
        ebuild =  self.selected_ebuild
        self.update_package_info(self.package, ebuild)

