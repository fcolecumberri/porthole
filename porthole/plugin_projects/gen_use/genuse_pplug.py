import genuse
import plugin
import utils
import genuse_pplug
#from utils import dprint

app = None
manager = None
menuitem = False
desc = "Generates USE Variables"
initialized = False
enabled = False

def new_instance( my_manager ):
    gui_output = True # Set this to False to stop the gui popup window with the use var
    stand_alone = True
    genuse_pplug.manager = my_manager
    genuse_pplug.initialized = True

def destroy_instance( ):
    if genuse_pplug.initialized == True:
        disable_plugin()    
    if app:
        app.destroy_cb()
    genuse_pplug.manager.del_menuitem( menuitem )
    genuse_pplug.initialized = False
    
def enable_plugin():
    if initialized == False:
        return
    genuse_pplug.menuitem = genuse_pplug.manager.new_menuitem("Generate USE Vars")
    genuse_pplug.menuitem.connect("activate", show_dialog )
    genuse_pplug.enabled = True

def disable_plugin():
    if genuse_pplug.initialized == False:
        return
    genuse_pplug.manager.del_menuitem( genuse_pplug.menuitem )
    genuse_pplug.enabled = False

def show_dialog( *args ):
    app = genuse.Use_App(True,False)
    app.show_all()

event_table = {
    "load" : new_instance,
    "reload" : new_instance,
    "unload" : destroy_instance,
    "enable" : enable_plugin,
    "disable" : disable_plugin
}
