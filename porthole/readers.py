#!/usr/bin/env python

'''
    Porthole Reader Classes
    The main interface the user will interact with

    Copyright (C) 2003 - 2004 Fredrik Arnerup, Brian Dolbec, 
    Daniel G. Taylor and Wm. F. Wheeler

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

import threading, re, gtk, os
import portagelib
from views import DependsView, CommonTreeView
from utils import get_icon_for_package, get_icon_for_upgrade_package, dprint


class CommonReader(threading.Thread):
    """ Common data reading class that works in a seperate thread """
    def __init__(self):
        """ Initialize """
        threading.Thread.__init__(self)
        # for keeping status
        self.count = 0
        # we aren't done yet
        self.done = False
        # cancelled will be set when the thread should stop
        self.cancelled = False
        # quit even if thread is still running
        self.setDaemon(1)

    def please_die(self):
        """ Tell the thread to die """
        self.cancelled = True

class UpgradableReader(CommonReader):
    """ Read available upgrades and store them in a treemodel """
    def __init__(self, upgrade_view, installed, upgrade_only, view_prefs):
        """ Initialize """
        CommonReader.__init__(self)
        self.upgrade_view = upgrade_view
        # dummy view to get dependancy's from existing depends.py code
        self.dep_view = DependsView()
        #self.upgrade_results = upgrade_view.upgrade_model
        self.upgrade_results = upgrade_view.get_model()
        self.installed_items = installed
        self.upgrade_only = upgrade_only
        #self.world = []
        self.view_prefs = view_prefs
        self.upgradables = {}
        self.world_count = 0
        self.dep_count = 0
 
    def run(self):
        """fill upgrade tree"""
        dprint("READERS: UpgradableReader(); process id = %d *******************" %os.getpid())
        self.upgrade_results.clear()    # clear the treemodel
        installed_world = []
        installed_dep = []
        upgradeflag = self.upgrade_only and True or False
        # find upgradable packages
        for cat, packages in self.installed_items:
            for name, package in packages.items():
                self.count += 1
                if self.cancelled: self.done = True; return
                upgradable = package.is_upgradable()
                if upgradable: # is_upgradable() = 1 for upgrade, -1 for downgrade
                    if upgradable == 1 or not self.upgrade_only:
                        if package.in_world:
                            installed_world.append([package.full_name, package])
                        else:
                            installed_dep.append([package.full_name, package])
                        self.upgradables[package.full_name] = package
        installed_world = portagelib.sort(installed_world)
        installed_dep = portagelib.sort(installed_dep)
        self.upgrade_total = len(installed_world) + len(installed_dep)
        self.world_count = 0
        self.dep_count = 0
        # show a temporary model while we add stuff to it (significant speedup)
        gtk.threads_enter()
        self.upgrade_view.remove_model()
        gtk.threads_leave()
        for full_name, package in installed_world:
            self.world_count += 1
            self.add_package(full_name, package, package.in_world)
            if self.cancelled: self.done = True; return
            #self.check_deps(full_name, package)
        if installed_dep != []:
            self.add_package(_("Upgradable dependencies:"), None, False, False)
            for full_name, package in installed_dep:
                self.dep_count += 1
                if self.cancelled: self.done = True; return
                self.add_deps(full_name, package, package.in_world, False)
                #self.check_deps(full_name, package)
        # restore upgrade model
        gtk.threads_enter()
        self.upgrade_view.restore_model()
        gtk.threads_leave()
        # set the thread as finished
        self.done = True

    def check_deps(self, full_name, package):
        """checks for and adds any upgradable dependencies to the tree"""
        dprint("READERS: check_deps(); Checking dependencies...")
        self.dep_view.clear()
        self.dep_view.fill_depends_tree(self.dep_view, package)
        self.model = self.dep_view.get_model()
        iter = self.model.get_iter_first()
        self.dep_list = []
        self.deps_checked = []
        self.get_upgrade_deps(iter, full_name)
        #
        # read the upgrade tree into a list of packages to upgrade
        #self.model.foreach(self.tree_node_to_list)
        if self.cancelled: self.done = True; return
        if self.dep_list != []:
            for f_name, pkg, blocker in self.dep_list:
                if self.cancelled: self.done = True; return
                self.add_deps(pkg.full_name, pkg, pkg.in_world, blocker)


    def add_package(self, full_name, package, in_world, header_icon = False):
        """Add a package to the upgrade TreeStore"""
        self.parent = self.upgrade_results.insert_before(None, None)
        self.upgrade_results.set_value(self.parent, 1, in_world)
        self.upgrade_results.set_value(self.parent, 4, in_world)
        self.upgrade_results.set_value(self.parent, 0, full_name)
        self.upgrade_results.set_value(self.parent, 2, package)
        # get an icon for the package
        icon, color = get_icon_for_upgrade_package(package, self.view_prefs)
        if header_icon:
            icon = gtk.STOCK_SORT_ASCENDING
        self.upgrade_results.set_value(self.parent, 5 , color)
        self.upgrade_results.set_value(self.parent, 3, self.upgrade_view.render_icon(icon,
                             size = gtk.ICON_SIZE_MENU,
                             detail = None))
        if package:
            self.upgrade_results.set_value(self.parent, 6, package.get_size())
            installed = package.get_latest_installed()
            latest = package.get_best_ebuild()
            try:
                installed = installed = portagelib.get_version( installed )
            except IndexError:
                installed = ""
            try:
                latest = portagelib.get_version( latest )
            except IndexError:
                latest = "Error"
            self.upgrade_results.set_value(self.parent, 7, installed)
            self.upgrade_results.set_value(self.parent, 8, latest)
            self.upgrade_results.set_value(self.parent, 9, package.get_properties().description )

    def get_upgrade_deps(self, iter, parent_name):
        list = []
        while iter:
                #dprint("READERS: get_upgrade_deps();processing iter: model.get_value(iter, 0) %s" %self.model.get_value(iter, 0))
                blocker = False
                ignore = False
                version = None
                package = self.model.get_value(iter, 2)
                if package:
                    full_name = package.full_name
                    #dprint("READERS: get_upgrade_deps(); processing package: %s" %full_name)
                    if full_name[0] == '!':
                        blocker = True
                    if full_name[0] == '=':
                        require_version = True
                    while full_name[0] in ['<','>','=','!']:
                        full_name = full_name[1:]
                    if full_name[-1] == '*':
                        full_name = full_name[:-1]
                    #dprint("READERS: get_upgrade_deps(); OPS cleaned; new full_name = %s" %full_name)
                    full_name = str(full_name)
                    name = full_name.split('/')
                    if len(name) != 2:
                        dprint("READERS: get_upgrade_deps(); dependancy name error for %s !!!!!!!!!!!!!!!!!!!!!!" %full_name)
                        return
                    if name[0] == 'virtual': # get a proper package name
                        old_name = name[0]
                        if name[1].count('-') or name[1].count('.'):
                            full_name = portagelib.extract_package(full_name)
                            dprint("READERS: get_upgrade_deps(); extracted virtual name = %s " %full_name)
                        if portagelib.virtuals.has_key(full_name):
                            full_name = portagelib.virtuals[full_name][0]
                        else:
                            dprint("READERS: get_upgrade_deps(); Key error for virtual name = %s " %full_name)
                            break
                        #dprint("READERS: get_upgrade_deps(); %s evaluated to %s" %(old_name+"/"+name[1], full_name))
                        if blocker and full_name == parent_name:
                            blocker = False
                            ignore = True # Ignore the self blocking package
                    elif name[1].count('-') or name[1].count('.'):
                        full_name = portagelib.extract_package(full_name)
                        if blocker and full_name <> None:
                            version = portagelib.get_version(full_name)
                    if full_name and not full_name in self.deps_checked:
                        #if full_name:
                        self.deps_checked.append(full_name)
                        #dprint("READERS: get_upgrade_deps(); extracted dep name = %s" %full_name)
                        if blocker:
                            pkg = portagelib.Package(full_name)
                            if pkg.get_installed():
                                if version and version in pkg.get_installed():
                                    self.dep_list += [(full_name, pkg, blocker)]
                                else:
                                    self.dep_list += [(full_name, pkg, blocker)]
                        elif not ignore and self.upgradables.has_key(full_name): # or not self.model.get_value(iter, 3):
                            pkg = portagelib.Package(full_name)
                            if self.model.iter_has_child(iter):
                                # check for dependency upgrades
                                child_iter = self.model.iter_children(iter)
                                self.get_upgrade_deps(child_iter, full_name)
                            self.dep_list += [(full_name, pkg, blocker)]
                    else: # Failed to extract the package name
                            dprint("READERS: get_upgrade_deps(); failed to get extracted package ==> dep name = %s" %full_name)
                else:
                    #dprint(self.model.iter_has_child(iter))
                    if self.model.iter_has_child(iter):
                        # check for dependency upgrades
                        child_iter = self.model.iter_children(iter)
                        self.get_upgrade_deps(child_iter, parent_name)
                    else:
                        dprint("READERS: get_upgrade_deps(); !!!!!!!!!!!!!!!!!!!!!!!!!! package = None")
                iter = self.model.iter_next(iter)
        return

    def tree_node_to_list(self, model, path, iter):
        """callback function from gtk.TreeModel.foreach(),
           used to add packages to an upgrades list"""
        if model.get_value(iter, 2):
                #dprint("processing iter: model.get_value(iter, 0) %s" %self.model.get_value(iter, 0))
                package = self.model.get_value(iter, 2)
                if package:
                    full_name = package.full_name
                    dprint("READERS: tree_node_to_list(); processesing package: %s" %full_name)
                    while full_name[0] in ['<','>','=']:
                        full_name = full_name[1:]
                    #~ if full_name.split('/')[1].count('.'):
                    full_name = portagelib.extract_package(full_name)
                    if full_name:
                        dprint("READERS: tree_node_to_list();extracted dep name = %s" %full_name)
                        pkg = portagelib.Package(full_name)
                        if (pkg.upgradable()):# or not self.model.get_value(iter, 3):
                            self.dep_list += [(full_name, pkg)]
        return False


    def add_deps(self, full_name, package, in_world, blocker):
        """Add all dependencies to the tree"""
        #dprint("READERS: add_deps();  name = %s" %full_name)
        child_iter = self.upgrade_results.insert_before(self.parent, None)
        self.upgrade_results.set_value(child_iter, 1, in_world)
        self.upgrade_results.set_value(child_iter, 4, in_world)
        self.upgrade_results.set_value(child_iter, 0, full_name)
        self.upgrade_results.set_value(child_iter, 2, package)
        installed = package.get_latest_installed()
        best = package.get_best_ebuild()
        #dprint("READERS: add_deps(); installed = %s" % str(installed))
        #dprint("READERS: add_deps(); best = %s" % str(best))
        try:
            if installed:
                instver = portagelib.get_version(installed)
        except IndexError:
            dprint("READERS: add_deps(); Installed ??? : %s" % str(installed))
            installed = ""
        try:
            if best:
                bestver = portagelib.get_version(best)
        except IndexError:
            bestver = "Error"
        self.upgrade_results.set_value(child_iter, 6, package.get_size())
        self.upgrade_results.set_value(child_iter, 7, instver)
        self.upgrade_results.set_value(child_iter, 8, bestver)
        self.upgrade_results.set_value(child_iter, 9, package.get_properties().description )
        if blocker:
            icon, color = gtk.STOCK_STOP, 'red'
        else:
            icon, color = get_icon_for_upgrade_package(package, self.view_prefs) #gtk.STOCK_GO_UP
        self.upgrade_results.set_value(child_iter, 5, color)
        self.upgrade_results.set_value(child_iter, 3, self.upgrade_view.render_icon(icon,
                                       size = gtk.ICON_SIZE_MENU, detail = None))

class DescriptionReader(CommonReader):
    """ Read and store package descriptions for searching """
    def __init__(self, packages):
        """ Initialize """
        CommonReader.__init__(self)
        self.packages = packages

    def run(self):
        """ Load all descriptions """
        dprint("READERS: DescriptionReader(); process id = %d *****************" %os.getpid())
        self.descriptions = {}
        for name, package in self.packages:
            if self.cancelled: self.done = True; return
            self.descriptions[name] = package.get_properties().description
            if not self.descriptions[name]:
                dprint("READERS: DescriptionReader(); No description for " + name)
            self.count += 1
        self.done = True
