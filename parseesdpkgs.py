#!/usr/bin/python3
# encoding: utf-8
"""
parseesdpkgs.py

!!DESCRIPTION GOES HERE!!

Copyright (C) University of Oxford 2019
    Ben Goodstein <ben.goodstein at it.ox.ac.uk>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import installinstallmacos as iim
import sys
import os
import glob
import plistlib
import subprocess
import json
import pprint

def get_system_version(basesystemdmg):
    mountpoint = iim.mountdmg(basesystemdmg)
    if mountpoint:
        sysversion_plist = os.path.join(mountpoint,
            "System/Library/CoreServices/SystemVersion.plist")
        with open(sysversion_plist, "rb")  as f:
            sysversion = plistlib.readPlist(f)
        iim.unmountdmg(mountpoint)
    return (sysversion['ProductVersion'], sysversion['ProductBuildVersion'])


def get_files(installesd):
    files = []
    mountpoint = iim.mountdmg(installesd)
    if mountpoint:
        pkgs = glob.glob(os.path.join(mountpoint, "Packages/*.pkg"))
        for pkg in pkgs:
            cmd = ["/usr/sbin/pkgutil", "--bom", pkg]
            try:
                bom = subprocess.check_output(cmd, universal_newlines=True)
                bom = bom.strip('\n')
                cmd = ["/usr/bin/lsbom", os.path.realpath(bom)]
                lsbom = subprocess.check_output(cmd, universal_newlines=True)
                files = files + [f.split('\t') for f in lsbom.split('\n')]
            except Exception:
                continue
        iim.unmountdmg(mountpoint)
    return files


def main():
    try:
        with open('boms.json', 'r') as f:
            boms = json.load(f)
    except:
        boms = {}
    dmgs = sys.argv[1:]
    for dmg in dmgs:
        mountpoint = iim.mountdmg(dmg)
        if mountpoint:
            basesystem = glob.glob(os.path.join(mountpoint,
                "Install*.app/Contents/SharedSupport/BaseSystem.dmg"))[0]
            if basesystem:
                os_vers, build_vers = get_system_version(basesystem)
            else:
                print("Could not ascertain OS and build version")
                continue
            installesd = glob.glob(os.path.join(mountpoint,
                "Install*.app/Contents/SharedSupport/InstallESD.dmg"))[0]
            if installesd:
                files = get_files(installesd)
                for f in files:
                    path, *rest = f
                    if path:
                        mode, owners, *rest = rest
                        if rest:
                            size, crc, *rest = rest
                            if rest:
                                symlink = rest[0]
                            else:
                                symlink = None
                        else:
                            size = None
                            crc = None
                            symlink = None
                    if not boms.get(path):
                        boms[path] = {}
                    if not boms[path].get(build_vers):
                        boms[path][build_vers] = {}
                    boms[path][build_vers]['mode'] = mode
                    boms[path][build_vers]['owners'] = owners
                    boms[path][build_vers]['size'] = size
                    boms[path][build_vers]['crc'] = crc
                    boms[path][build_vers]['symlink'] = symlink
                iim.unmountdmg(mountpoint)
    with open('boms.json', 'w') as f:
        json.dump(boms, f)


if __name__ == "__main__":
    main()
