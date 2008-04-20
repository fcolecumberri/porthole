#!/usr/bin/env python

'''
    Porthole Reader Class: ToolChain

    Copyright (C) 2008 Brian Dolbec, Heil Van Camp
    This class is based on Heil's emwrap.sh script for rebuilding your toolchain

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

from porthole.utils import debug
from porthole import backends
portage_lib = backends.portage_lib


class ToolChain:
    """Class to handle all toolchain related info and decisions"""
    def __init__( self, build ):
        self.build = build
        self.tc_conf = ""
        self.tc_stdc = ""
        self.TC_build = ["sys-kernel/linux-headers", "sys-libs/glibc", tc_conf, \
                      "sys-devel/binutils", "sys-devel/gcc", tc_stdc]
        self.TC="linux-headers glibc $tc_conf_regx binutils-[0-9].* gcc-[0-9].* glibc binutils-[0-9].* gcc-[0-9].* $tc_stdc"
        self.TC_glb="glibc $tc_conf_regx binutils-[0-9].* gcc-[0-9].* glibc binutils-[0-9].* gcc-[0-9].* $tc_stdc"
        self.TCmini="$tc_conf_regx binutils-[0-9].* gcc-[0-9].* binutils-[0-9].* gcc-[0-9].* $tc_stdc"
        self.TC1="linux-headers glibc $tc_conf_regx binutils-[0-9].* gcc-[0-9].* $tc_stdc"
        self.TC_glb1="glibc $tc_conf_regx binutils-[0-9].* gcc-[0-9].* $tc_stdc"
        self.TCmini1="$tc_conf_regx gcc-[0-9].* binutils-[0-9].* $tc_stdc"

