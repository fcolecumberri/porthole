#!/usr/bin/env python
#

# (C) Copyright 2002 Bob Phan
# This is GPLed software.
#
# File:     genuse
# Author:   Bob Phan <bob@endlessrecursion.net>
# This code was adopted for use in Porthole by Brian Bockelman
# Original program: generate_use Version:  0.2

# (C) Copyright 2004 Brian Bockelman, Brian Dolbec
#
# Description:
#   Auto-generates a USE variable.  You check whatever you
#   want, and after comparison against the defaults, it will
#   generate the smallest USE variable that will give you
#   desired results
#
#   NOTE: This does not yet take into effect auto-use variables.
#         Consult /etc/make.profile/use.defaults and the portage
#         use guide to see what is going on there.
#

#
# If you don't like the gui popup window, scroll to the bottom
# of this code and change the True to a False where marked.
#

import gtk,os,shutil,pty
from gtk import TRUE,FALSE
from   string import *
import re


class UseInfo:
    def __init__( self ):
        self.use_desc_fn = '/usr/portage/profiles/use.desc'
        self.make_def_fn = '/etc/make.profile/make.defaults'
        self.make_con_fn = '/etc/make.conf'
        self.test_make_con_fn = os.path.expanduser('~')+'/.test_make.conf'
        self.available = {}
        self.defaults  = []
        self.conf      = []

    def get_defaults( self ):
        if self.defaults != []:
            return self.defaults

        file = open( self.make_def_fn )
        re_use_end   = re.compile( "\"[ \t]*" )
        re_use_begin = re.compile( "^[ \t]*USE[ \t]*=[ \t]*\"" )

        in_use = False
        for line in file.readlines():
            match = re_use_begin.match( line )
            if match:
                in_use = True
            if in_use:
                line = re_use_begin.sub( '', line )
                match = re_use_end.search( line )
                if match:
                    in_use = False
                    line = re_use_end.sub( '', line )
                self.defaults.extend( split( line ) )

        return self.defaults

    def get_conf( self ):
        if self.conf != []:
            return self.conf
        self.pre_use = ''
        self.post_use = ''
        Preamble = True
        get_remainder = False

        file = open( self.make_con_fn )
        re_use_begin = re.compile( "^[ \t]*USE[ \t]*=[ \t]*\"" )
        re_use_end   = re.compile( "\"[ \t]*" )

        is_use = False
        for line in file.readlines():
            #~print line
            if get_remainder:
                self.post_use += line
            else:
                begin_match = re_use_begin.match( line )
                if begin_match:
                    #print "Match: USE line found"
                    is_use = True
                    Preamble = False
                elif Preamble: # save it  to  pre_use
                    self.pre_use += line

                if is_use:
                    line = re_use_begin.sub( '', line )
                    #print "new line = :" + line
                    end_match = re_use_end.search( line )
                    if end_match:
                        is_use = False
                        get_remainder = True
                        line = re_use_end.sub( '', line )
                        #print "end found, line = :" + line
                    self.conf.extend( split( line ) )

        return self.conf

    def get_available( self ):
        if self.available != {}:
            return self.available

        file = open( self.use_desc_fn )
        rex  = re.compile( "^([A-Za-z0-9+]+)[ \t]+-[ \t]+(.*)" )
        for line in file.readlines():
            match = rex.match( line )
            if match:
                self.available[ match.group(1) ] = match.group(2)
        file.close()
        return self.available

    def generate_var( self, requested, full ):
        use_string = 'USE="'
        line = ''
        use_keys = self.available.keys()
        use_keys.sort()
        for use in use_keys: #self.available.keys():
            if len(line) > 70:
                use_string += line + "\\" + "\n"
                line = '     '
            default = False
            request = False
            if self.defaults.__contains__( use ):
                default = True
            if requested.__contains__( use ):
                request = True

            if full:
                if request:
                    line += use + " "
                else:
                    line += "-" + use + " "
            else:
                if request and not default:
                    line += use + " "
                if not request and default:
                    line += "-" + use + " "

        use_string += line
        use_string = use_string.rstrip()
        use_string = use_string + '"'

        return use_string

class Use_App( gtk.Window ):
    def __init__( self, gui_dump, is_app=False ):
        self.is_app=is_app
        gtk.Window.__init__( self, gtk.WINDOW_TOPLEVEL )
        self.connect( "destroy", self.destroy_cb )
        self.use_info = UseInfo()
        self.use_checks = {}
        self.GUI_DUMP = gui_dump

        # Add widgets
        self.vbox = gtk.VBox()
        self.hbox = gtk.HBox()
        self.create_list()
        self.create_buttons()

        self.set_default_size( 640, 480 )
        self.add( self.vbox )

        # Create display box
        self.display_box = gtk.Window()
        self.display_box.set_title("Use Var - Changes made to make.conf")
	self.db_vbox = gtk.VBox()
	self.display_box.add( self.db_vbox )
	self.db_label = gtk.Label("Should porthole make the following changes to make.conf?")
	self.db_vbox.add( self.db_label )
        self.textbuffer = gtk.TextBuffer(None)
        self.text = gtk.TextView()
        self.text.set_buffer(self.textbuffer)
        self.text.set_wrap_mode(gtk.WRAP_WORD)
        self.db_vbox.add( self.text )
	self.create_display_buttons()
        self.display_box.set_default_size( 620, 200 )
        self.display_box.connect( "delete_event", self.display_box_destroy_cb )
        self.box_showing = False

    def create_list( self ):
        scroll   = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_NEVER,gtk.POLICY_AUTOMATIC)
        vbox     = gtk.VBox(False, 2)
        use_vars = self.use_info.get_available()
        keys     = use_vars.keys()
        keys.sort()
        for use in keys:
            hbox   = gtk.HBox()
            button = gtk.CheckButton( label=use )
            button.set_size_request( 100, -1 )

            textview = gtk.TextView()
            textview.set_editable(False)
            textview.set_wrap_mode(gtk.WRAP_WORD)
            textbuffer = textview.get_buffer()
            textbuffer.set_text( use_vars[use] )
            
            hbox.pack_start( button, expand=FALSE, fill=FALSE, padding=1 )
            hbox.pack_start( textview, expand=TRUE, fill=TRUE, padding=1 )

            self.use_checks[use] = button
            vbox.add( hbox )

        defaults = self.use_info.get_defaults()
        for use in defaults:
            if self.use_checks.has_key( use ):
                button = self.use_checks[use]
                button.set_active( TRUE )
            else:
                print "Use variable '" + use + "' not found in use.desc!"

        conf = self.use_info.get_conf()
        re_remove = re.compile( "^-" )
        for use in conf:
            remove_me = re_remove.match( use )
            use = re_remove.sub( '', use )
            if self.use_checks.has_key( use ):
                button = self.use_checks[use]
                if remove_me:
                    button.set_active( FALSE )
                else:
                    button.set_active( TRUE )

        scroll.add_with_viewport(vbox)
        self.vbox.pack_start( scroll, expand=TRUE, fill=TRUE, padding=1 )

    def create_buttons( self ):
        hbox = gtk.HBox(1)
        hbox.set_size_request( -1, 35 )

        button = gtk.Button( "Create USE" )
        button.connect( "clicked", self.dump_cb, 0 )
        hbox.add( button )

        button = gtk.Button( "Exit" )
        button.connect( "clicked", self.destroy_cb )
        hbox.add( button )

        self.vbox.pack_start( hbox, expand=FALSE, fill=FALSE, padding=1 )

    def create_display_buttons( self ):
	hbox = gtk.HBox(1)
	hbox.set_size_request( -1, 35 )
	button = gtk.Button( "Yes" )
	button.connect( "clicked", self.display_box_write_changes )
	hbox.add( button )
	button = gtk.Button( "No" )
	button.connect( "clicked", self.display_box_destroy_cb )
	hbox.add( button )
	self.db_vbox.pack_start( hbox, expand=FALSE, fill=FALSE, padding=1 )
	

    def dump_cb( self, *args ):
        requested = []
        full = args[1]
        for use in self.use_checks.keys():
            button = self.use_checks[use]
            if button.get_active():
                requested.append( use )
        self.use_var = self.use_info.generate_var( requested, full )
        self.text.set_editable( True )
        #self.text.delete_text( 0, -1 )
	
        #shutil.move( self.use_info.make_con_fn, self.use_info.make_con_fn + ".backup" )
        #fout = open( self.use_info.make_con_fn,'w' )
	
	#First, write the temp file
        self.write_file( self.use_info.test_make_con_fn )

	#Then, run diff between the temp file and make.conf
            
	# run the commandbuffer.tag_table.lookup(tagname)
	command_string = 'diff -u ' + self.use_info.make_con_fn + ' ' + self.use_info.test_make_con_fn
	self.fd = os.popen(command_string)

	read_string = 'start' 
	diff_text = ''
	while read_string != '':
	    read_string = self.fd.readline()
	    diff_text += read_string

	#Now, show the diff and ask for approval!
        if self.box_showing:
            self.textbuffer.set_text('')
        self.textbuffer.insert_at_cursor( diff_text,len(diff_text) )
        if self.GUI_DUMP:
            self.display_box.show_all()
        self.box_showing = True
        self.text.set_editable( False )

								    
    def write_file( self, file_name ):
        fout = open( file_name, 'w' )
	fout.write( self.use_info.pre_use )
	fout.write( self.use_var )
	fout.write( '\n' )
	fout.write( self.use_info.post_use )
        fout.close()

    def destroy_cb( self, *args ):
        self.destroy()
        if self.is_app:
            gtk.main_quit()
	
    def display_box_destroy_cb( self, *args ):
        self.display_box.hide()
        self.textbuffer.set_text('')
        self.box_showing = False
        return True

    def display_box_write_changes( self, *args ):
    	self.display_box_destroy_cb( 0 )
    	return self.write_file( self.use_info.make_con_fn )
	

if __name__ == '__main__':
    gui_output = True # Set this to False to stop the gui popup window with the use var
    stand_alone = True
    app = Use_App(gui_output,stand_alone) 
    app.show_all()
    gtk.main()
