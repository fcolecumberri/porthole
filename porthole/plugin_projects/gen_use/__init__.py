#!/usr/bin/env python
#

import genuse
#import plugin
#import utils
#import genuse_pplug
from utils import dprint

app = None
manager = None
menuitem = False
desc = "Generates USE Variables"
initialized = False
enabled = False

def new_instance(my_manager):
    global gui_output, stand_alone, manager, initialized
    gui_output = True # Set this to False to stop the gui popup window with the use var
    stand_alone = True
    #genuse_pplug.manager = my_manager
    #genuse_pplug.initialized = True
    manager = my_manager
    initialized = True
    dprint("GEN_USE: new_instance: initialized okay")
    return True

def destroy_instance( ):
    global manager, initialized
    #if genuse_pplug.initialized == True:
    if initialized == True:
        disable_plugin()    
    if app:
        app.destroy_cb()
    #genuse_pplug.manager.del_menuitem( menuitem )
    manager.del_menuitem(menuitem)
    #genuse_pplug.initialized = False
    initialized = False
    dprint("GEN_USE: destroy_instance: destroyed")
    return True
    
def enable_plugin():
    global menuitem, enabled, initialized
    if initialized == False:
        dprint("GEN_USE: enable_plugin: not initialized!")
        return False
    #genuse_pplug.menuitem = genuse_pplug.manager.new_menuitem("Generate USE Vars")
    #genuse_pplug.menuitem.connect("activate", show_dialog )
    #genuse_pplug.enabled = True
    dprint("GEN_USE: enable_plugin: generating new menuitem")
    menuitem = manager.new_menuitem("Generate USE Vars")
    menuitem.connect("activate", show_dialog)
    enabled = True
    return True

def disable_plugin():
    global manager, enabled
    #if genuse_pplug.initialized == False:
    if initialized == False:
        return
    #genuse_pplug.manager.del_menuitem( genuse_pplug.menuitem )
    #genuse_pplug.enabled = False
    manager.del_menuitem(menuitem)
    enabled = False

def show_dialog( *args ):
    global app
    app = genuse.Use_App(True,False)
    app.show_all()

event_table = {
    "load" : new_instance,
    "reload" : new_instance,
    "unload" : destroy_instance,
    "enable" : enable_plugin,
    "disable" : disable_plugin
}
