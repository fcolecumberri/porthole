#!/usr/bin/env python

import gtk, webbrowser, portagelib, pango

class Summary(gtk.TextView):
    def __init__(self):
        gtk.TextView.__init__(self)
        tagtable = self.create_tag_table()
        self.buffer = gtk.TextBuffer(tagtable)
        self.set_buffer(self.buffer)
        self.connect("motion_notify_event", self.on_mouse_motion)

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
                       'scale': pango.SCALE_X_LARGE}),
             'description': ({"style": pango.STYLE_ITALIC}),
             'url': ({'foreground': 'blue'}),
             'property': ({'weight': pango.WEIGHT_BOLD}),
             'value': ({})
             })
        # React when user clicks on the homepage url
        self.url_tag = table.lookup('url')
        self.url_tag.connect("event", self.on_url_event)
        return table
    
    def on_url_event(self, tag, widget, event, iter):
        """Catch when the user clicks the url"""
        if event.type == gtk.gdk.BUTTON_RELEASE:
            try: webbrowser.open(self.homepages[0])
            except: pass

    def on_mouse_motion(self, widget, event, data = None):
        # we need to call get_pointer, or we won't get any more events
        pointer = self.window.get_pointer()
        x, y, spam = pointer
        x, y = self.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, x, y)
        i = self.get_iter_at_location(x, y)
        is_url = i.has_tag(self.url_tag)
        self.url_tag.set_property(
            "underline", 
            is_url and pango.UNDERLINE_SINGLE or pango.UNDERLINE_NONE)
        self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(
            is_url and gtk.gdk.Cursor(gtk.gdk.HAND2) or None)
        return gtk.FALSE

    def update_package_info(self, package):
        """Update the notebook of information about a selected package"""

        def append(text, tag = None):
            """Append (unicode) text to summary buffer."""
            iter = self.buffer.get_end_iter()
            buffer = self.buffer
            if tag: buffer.insert_with_tags_by_name(iter, text, tag)
            else: buffer.insert(iter, text)

        def nl(): append("\n")
        
        self.buffer.set_text("", 0)
        if not package:
            #it's really a category selected!
            return
        #read it's info
        metadata = package.get_metadata()
        ebuild = package.get_latest_ebuild()
        installed = package.get_installed()
        versions = package.get_versions(); versions.sort()
        props = package.get_properties()
        description = props.description
        homepages = props.get_homepages() # may be more than one
        self.homepages = homepages  # store url for on_url_event
        use_flags = props.get_use_flags()
        license = props.license
        slot = unicode(props.get_slot())
        #build info into buffer
        append(package.full_name, "name"); nl()
        if description:
            append(description, "description"); nl()
        if metadata and metadata.longdescription:
            nl(); append(metadata.longdescription, "description"); nl()
        for homepage in homepages: append(homepage, "url"); nl()
        nl()         #put a space between this info and the rest
        if installed:
            append("Installed versions: ", "property")
            append(", ".join([portagelib.get_version(ebuild)
                              for ebuild in installed]),
                   "value")
        else:
            append("Not installed", "property")
        nl()
        if versions:
            append("Available versions: ", "property")
            append(", ".join([portagelib.get_version(ebuild)
                              for ebuild in versions]),
                   "value")
            nl()
        nl()         #put a space between this info and the rest, again
        if use_flags:
            append("Use Flags: ", "property")
            append(", ".join(use_flags), "value")
            nl()
        if license:
            append("License: ", "property"); append(license, "value"); nl()
        if slot:
            append("Slot: ", "property"); append(slot, "value"); nl()
