# -*- coding: utf-8 -*-
#
""" File: porthole/views/markup.py
This file is part of the Porthole, a graphical portage-frontend.

   Copyright (C) 2003 - 2010 Fredrik Arnerup, Daniel G. Taylor,
    Brian Dolbec, Tommy Iorns

This is free software.  You may redistribute copies of it under the terms of
the GNU General Public License version 2.
There is NO WARRANTY, to the extent permitted by law.

Written by, Brian Dolbec <dol-sen@users.sourceforge.net>
based on accumulated code fron the original summary.py module
"""


from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango

from porthole.loaders.loaders import load_web_page



class URLObject(object):
    """Structure to hold all relavent data about the url to
    be used to correctly process and produce the desired result"""

    def __init__(self, text='', url='', color='blue', type='', tag=None, handler=None):
        """Optional handler function to use to act on the url"""
        self.text = text
        self.url = url
        self.color = color
        self.type = type
        self.tag = tag
        self.handler = handler


class MarkupView (object):
    """Markup class which adds markup highlighting and text formatting
    to the subclassed textview
    """

    def __init__ (self):

        self.set_editable(False)
        self.set_cursor_visible(False)
        margin = 10
        self.set_left_margin(margin)
        self.set_right_margin(margin)
        self.tags = {'new_ver': ({'weight': Pango.Weight.BOLD,
                        'scale': 1.2, #Pango.SCALE_LARGE,
                        'pixels-above-lines': 5}),
                        'description': ({"style": Pango.Style.ITALIC}),
                        'url': ({'foreground': 'blue'}),
                        'update': ({'weight': Pango.Weight.BOLD}),
                        'developer':({'foreground': 'darkblue'}),
                        'normal': ({}),
                        'atom':({'foreground': 'magenta'}),
                        'added': ({'foreground':'darkgreen'}),
                        'removed':({'foreground':'red'}),
                        'masked': ({"style": Pango.Style.ITALIC}),
                        'date':({'foreground': 'darkorange'}),
                        'header':({'foreground': 'green'}),
        }

        tagtable = self._create_tag_table()
        self.buffer = Gtk.TextBuffer()
        self.set_buffer(self.buffer)

        # Capture any mouse motion in this tab so we
        # can highlight URL links & change mouse pointer
        self.connect("motion_notify_event", self.on_mouse_motion)

        # List of active URLs in the tab
        self.url_tags = []
        self.underlined_url = False
        self.reset_cursor = 'Please'


    def append_atom(self, atom):
        #atom = parts['atom']
        if atom.startswith('+'):
            self.append(' '+atom, 'added')
        elif atom.startswith('-'):
            self.append(' '+atom,  'removed')
        else:
            self.append(' '+atom,  'atom')
        return

    def append_developer(self, name):
        self.append(name, 'developer')

    def append_date(self, date, indent=' '):
        self.append(indent+date, 'date')

    def append_bug(self, bug):
        num = self.bug_re.search(bug).group()
        text = self.bug_re.split(bug)
        if text[0]:
            self.append(text[0],'normal')
        # need to track tag-id's due to multiple occurances of bug #
        _id = 'tag_id-%d' %self.bug_id
        self.bug_id += 1
        self.bugs[_id] = num
        self.append_url(num, _id, self.url_color)
        if text[1]:
            self.append(text[1],'normal')
        return

    def append(self, text, tag = None):
        """ Append (unicode) text to summary buffer """
        iter = self.buffer.get_end_iter()
        buffer = self.buffer
        # if tag: buffer.insert_with_tags_by_name(iter, text, tag)
        # else: buffer.insert(iter, text)
        buffer.insert(iter, text)

    def append_url(self, text, url, colour):
        """ Append URL to textbuffer and connect an event """
        tag = self.buffer.create_tag(url)
        tag.set_property("foreground", colour)
        tag.connect("event", self.on_url_event)
        self.url_tags.append(tag)
        self.append(text, tag.get_property("name"))

    def nl(self, x=1):
        """ Append x new lines to the buffer """
        self.append("\n"*x)

    def _create_tag_table(self):
        """ Define all markup tags """
        def create(descs):
            table = Gtk.TextTagTable()
            for name, properties in list(descs.items()):
                tag = Gtk.TextTag()
                tag.name = name
                table.add(tag)
                for property, value in list(properties.items()):
                    tag.set_property(property, value)
            return table

        table = create(self.tags)
        self.url_color = self.tags["url"]['foreground']
        return table

    def on_url_event(self, tag, widget, event, iter):
        """ Catch when the user clicks the URL """
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            bug=self.bugs[tag.get_property("name")]
            load_web_page(self.bugzilla_url+bug)

    def on_mouse_motion(self, widget, event, data = None):
        # fixme needs porting or cleaning
        # we need to call get_pointer, or we won't get any more events
        # pointer = self.get_window(Gtk.TextWindowType.TEXT).get_pointer()
        # x, y, spam = self.get_window(Gtk.TextWindowType.TEXT).get_pointer()
        # x, y = self.window_to_buffer_coords(Gtk.TextWindowType.TEXT, x, y)
        # # tags = self.get_iter_at_location(x, y).get_tags()
        # if self.underlined_url:
        #     self.underlined_url.set_property("underline", Pango.Underline.NONE)
        #     self.get_window(Gtk.TextWindowType.TEXT).set_cursor(None)
        #     self.underlined_url = None
        # # for tag in tags:
        # #     if tag in self.url_tags:
        # #         tag.set_property("underline", Pango.Underline.SINGLE)
        # #         self.get_window(Gtk.TextWindowType.TEXT).set_cursor(Gdk.Cursor
        # #                                                          (Gdk.HAND2))
        # #         self.underlined_url = tag
        # if self.reset_cursor: # defaults to Gdk.XTERM - reset it to None
        #     self.get_window(Gtk.TextWindowType.TEXT).set_cursor(None)
        #     self.reset_cursor = False
        return False
