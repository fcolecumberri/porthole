#!/usr/bin/env python

'''
    Porthole Mainwindow Action support
    Support class and functions for the mainwindow interface

    Copyright (C) 2003 - 2011
    Fredrik Arnerup, Brian Dolbec,
    Daniel G. Taylor, Wm. F. Wheeler, Tommy Iorns

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

from gettext import gettext as _

from porthole import config
from porthole import db

from porthole.utils import (
    debug,
    utils
)
from porthole import backends
PMS_LIB = backends.portage_lib
from porthole.advancedemerge.advemerge import AdvancedEmergeDialog
from porthole.dialogs.simple import SingleButtonDialog
from porthole.dialogs.command import RunDialog
from porthole.terminal.terminal import ProcessManager
from porthole.backends.utilities import get_sync_info

from porthole.mwsupport.category import CategoryHandler


class ActionHandler(CategoryHandler):
    '''Support functions for mainwindow actions'''

    def __init__(self):
        CategoryHandler.__init__(self)
        self.get_sync_time()
        self.new_sync = False
        # create and start our process manager
        self.process_manager = ProcessManager(utils.environment(), False)

    def package_update(self, pkg):
        """callback function to update an individual package
            after a successfull emerge was detected"""
        # find the pkg in db.db
        db.db.update(PMS_LIB.extract_package(pkg))

    def sync_callback(self):
        """re-initializes portage so it uses the new metadata cache
           then init our db"""
        #self.re_init_portage()
        PMS_LIB.settings.reset()
        # self.reload==False is currently broken for init_data when
        # reloading after a sync
        #self.init_data()
        self.new_sync = True
        self.reload_db()
        self.refresh()

    def get_sync_time(self):
        """gets and returns the timestamp info saved during
           the last portage tree sync"""
        self.last_sync, self.valid_sync = get_sync_info()

    def set_sync_tip(self):
        """Sets the sync tip for the new or old toolbar API"""
        self.widget["btn_sync"].set_has_tooltip(True)
        self.widget["btn_sync"].set_tooltip_text(' '.join([self.sync_tip,
                self.last_sync[:], '']))

    def action_callback(self, action = None, arg = None):
        """dispatcher interface callback to handle various actions."""
        debug.dprint("MAINWINDOW: action_callback(); " +
            "caller = %s, action = '%s', arg = %s"
            %(arg['caller'], str(action), str(arg)))
        if action in ["adv_emerge", "set path", "package changed", "refresh"]:
            # handle possible spaces in callback action string
            _action = action.replace(' ', '_')
            ret_val = None
            ret_val = getattr(self, "_action_%s_" %_action)(arg)
            if ret_val:
                return ret_val
        else:
            return self._action_install(action, arg)


    def _action_adv_emerge_(self, arg):
        """handle advanced emerge action callback"""
        if 'package' in arg:
            package = arg['package']
        elif 'full_name' in arg:
            package = db.db.get_package(arg['full_name'])
        else:
            debug.dprint("MAINWINDOW: _action_adv_emerge_(); did not get an "+
                    "expected arg variable for 'adv_emerge' action arg = " +
                    str(arg))
            return False
        self.adv_emerge_package( package)
        return True

    def _action_set_path_(self, arg):
        """handle a path setting callback"""
        # save the path to the package that matched the name passed
        # to populate() in PackageView... (?)
        x = self.widget["view_filter"].get_active()
        self.current_pkg_path[x] = arg['path'] # arg = path

    def _action_package_changed_(self, arg):
        """handle a package changed callback"""
        self.package_changed(arg['package'])
        return True

    def _action_refresh_(self, arg):
        """handle a refresh action callback"""
        self.refresh()
        return True

    def _action_install(self, action, arg):
        """handle install commnad callbacks"""
        old_pretend_value = config.Prefs.emerge.pretend
        old_verbose_value = config.Prefs.emerge.verbose
        if "emerge" in action:
            commands = ["emerge "]
        elif  "unmerge" in action:
            commands = ["emerge --unmerge "]
        if "pretend" in action:
            config.Prefs.emerge.pretend = True
        else:
            config.Prefs.emerge.pretend = False
        if "sudo" in action:
            commands = ['sudo -p "Password: " '] + commands
        commands.append(config.Prefs.emerge.get_string())
        if "ebuild" in arg:
            commands.append('=' + arg['ebuild'])
            cp = PMS_LIB.pkgsplit(arg['ebuild'])[0]
        elif 'package' in arg:
            cp = arg['package'].full_name
            commands.append(arg['package'].full_name)
        elif 'full_name' in arg:
            cp = arg['full_name']
            commands.append(arg['full_name'])
        else:
            debug.dprint("MAINWINDOW action_callback(): unknown arg '%s'"
                    % str(arg))
            return False
        self.setup_command(PMS_LIB.get_name(cp), ''.join(commands))
        config.Prefs.emerge.pretend = old_pretend_value
        config.Prefs.emerge.verbose = old_verbose_value
        return True

    def setup_command(self, package_name, command, run_anyway=False):
        """Setup the command to run or not"""
        if (self.is_root
                or run_anyway
                or (config.Prefs.emerge.pretend
                and not command.startswith(config.Prefs.globals.Sync))
                or command.startswith("sudo ")
                or utils.pretend_check(command)):
            if command.startswith('sudo -p "Password: "'):
                debug.dprint('MAINWINDOW: setup_command(); removing ' +
                    '\'sudo -p "Password: "\' for pretend_check')
                is_pretend = utils.pretend_check(command[21:])
            else:
                is_pretend = utils.pretend_check(command)
            debug.dprint("MAINWINDOW: setup_command(); emerge.pretend = " +
                "%s, pretend_check = %s, help_check = %s, info_check = %s"
                    %(str(config.Prefs.emerge.pretend), str(is_pretend),
                    str(utils.help_check(command)),
                    str(utils.info_check(command))))
            if (config.Prefs.emerge.pretend
                    or is_pretend
                    or utils.help_check(command)
                    or utils.info_check(command)):
                # temp set callback for testing
                #callback = self.sync_callback
                callback = lambda: None  # a function that does nothing
                debug.dprint("MAINWINDOW: setup_command(); " +
                    "callback set to lambda: None")
            elif package_name == "Sync Portage Tree":
                callback = self.sync_callback #self.init_data
                debug.dprint("MAINWINDOW: setup_command(); " +
                    "callback set to self.sync_callback")
            else:
                #debug.dprint("MAINWINDOW: setup_command(); " +
                    #"setting callback()")
                callback = self.reload_db
                debug.dprint("MAINWINDOW: setup_command(); " +
                    "callback set to self.reload_db")
                #callback = self.package_update
            #ProcessWindow(command, env, config.Prefs, callback)
            self.process_manager.add(package_name, command, callback,
                _("Porthole Main Window"))
        else:
            debug.dprint("MAINWINDOW: Must be root user to run command '%s' "
                % command)
            #self.sorry_dialog=utils.SingleButtonDialog(_("You are not root!"),
            #        self.mainwindow,
            #        _("Please run Porthole as root to emerge packages!"),
            #        None, "_Ok")
            self.check_for_root() # displays not root dialog
            return False
        return True

    def emerge_package(self, package, sudo=False):
        """Emerge the package."""
        if (sudo or (not utils.is_root() and utils.can_sudo())) \
                and not config.Prefs.emerge.pretend:
            self.setup_command(package.get_name(),
                'sudo -p "Password: " emerge'+
                config.Prefs.emerge.get_string() +
                package.full_name)
        else:
            self.setup_command(package.get_name(), "emerge" +
                config.Prefs.emerge.get_string() + package.full_name)

    def adv_emerge_package(self, package):
        """Advanced emerge of the package."""
        # Activate the advanced emerge dialog window
        # re_init_portage callback is for when package.use etc. are modified
        return AdvancedEmergeDialog(package, self.setup_command,
                self.re_init_portage)


    def unmerge_package(self, package, sudo=False):
        """Unmerge the package."""
        if (sudo or (not self.is_root and utils.can_sudo())) \
                and not config.Prefs.emerge.pretend:
            self.setup_command(package.get_name(),
                    'sudo -p "Password: " emerge --unmerge' +
                    config.Prefs.emerge.get_string() + package.full_name)
        else:
            self.setup_command(package.get_name(), "emerge --unmerge" +
                    config.Prefs.emerge.get_string() + package.full_name)

    def sync_tree(self, *widget):
        """Sync the portage tree and reload it when done."""
        sync = config.Prefs.globals.Sync
        if config.Prefs.emerge.verbose:
            sync += " --verbose"
        if config.Prefs.emerge.nospinner:
            sync += " --nospinner "
        if utils.is_root():
            self.setup_command("Sync Portage Tree", sync)
        elif utils.can_sudo():
            self.setup_command("Sync Portage Tree", 'sudo -p "Password: " ' +
                    sync)
        else:
            self.check_for_root()

    def open_log(self, widget):
        """ Open a log of a previous emerge in a new terminal window """
        newterm = ProcessManager(utils.environment(), True)
        newterm.do_open(widget, None)
        return

    def custom_run(self, *widget):
        """ Run a custom command in the terminal window """
        #debug.dprint("MAINWINDOW: entering custom_run")
        #debug.dprint(config.Prefs.run_dialog.history)
        RunDialog(self.setup_command, run_anyway=True)
        return

    def check_for_root(self, *args):
        """figure out if the user can emerge or not..."""
        if not self.is_root:
            self.no_root_dialog = SingleButtonDialog(
                _("No root privileges"),
                self.mainwindow,
                _("In order to access all the features of Porthole,\nplease run it with root privileges."
                ), self.remove_nag_dialog,
                _("_Ok"))

    def remove_nag_dialog(self, widget, response):
        """ Remove the nag dialog and set it to not display next time """
        self.no_root_dialog.destroy()
        config.Prefs.main.show_nag_dialog = False

