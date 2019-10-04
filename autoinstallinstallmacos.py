#!/usr/bin/python3
# encoding: utf-8
"""
autoinstallinstallmacos.py

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
# Python 3 compatibility shims
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import os
import datetime
import plistlib
import installinstallmacos as iim
import sys
import contextlib

DEFAULT_SUCATALOGS = {
    '17': 'https://swscan.apple.com/content/catalogs/others/'
          'index-10.13-10.12-10.11-10.10-10.9'
          '-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog',
    '18': 'https://swscan.apple.com/content/catalogs/others/'
          'index-10.14-10.13-10.12-10.11-10.10-10.9'
          '-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog',
}


SEED_CATALOGS_PLIST = (
    '/System/Library/PrivateFrameworks/Seeding.framework/Versions/Current/'
    'Resources/SeedCatalogs.plist'
)

workdir = "."


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()


def check_cache(workdir):
    cache_path = os.path.join(workdir, ".cache.plist")
    if os.path.isfile(cache_path):
        with open(cache_path, "rb") as f:
            return plistlib.load(f)


def write_cache(workdir, product_id, product):
    cache_path = os.path.join(workdir, ".cache.plist")
    products = {}
    if os.path.isfile(cache_path):
        with open(cache_path, "rb") as f:
            products = plistlib.load(f)
    products[product_id] = product
    with open(cache_path, "wb") as f:
        plistlib.dump(products, f)


def main():
    su_catalog_url = iim.get_default_catalog()

    with contextlib.redirect_stdout(None):
        catalog = iim.download_and_parse_sucatalog(
            su_catalog_url, workdir)
        product_info = iim.os_installer_product_info(
            catalog, workdir)

    if not product_info:
        print("No macOS installer products found in the sucatalog.",
              file=sys.stderr)
        exit(-1)

    cached_products = check_cache(workdir)
    if cached_products:
        print("Found product cache...")

    for product_id, product in product_info.items():
        if cached_products and product_id in cached_products.keys():
            print("Product %s is cached..." % product_id)
        else:
            print("Product %s is not in the cache, downloading..."
                  % product_id)

            iim.replicate_product(catalog, product_id,
                                  workdir, ignore_cache=True)
            # generate a name for the sparseimage
            volname = ('Install_macOS_%s-%s'
                       % (product_info[product_id]['version'],
                          product_info[product_id]['BUILD']))

            # Create output directory
            if not os.path.exists(os.path.join(workdir, "output")):
                os.mkdir(os.path.join(workdir, "output", mode=0o775))
            sparse_diskimage_path = os.path.join(workdir, "output",
                                                 volname + '.sparseimage')
            if os.path.exists(sparse_diskimage_path):
                os.unlink(sparse_diskimage_path)

            # make an empty sparseimage and mount it
            print('Making empty sparseimage...')
            sparse_diskimage_path = iim.make_sparse_image(
                                        volname,
                                        sparse_diskimage_path)
            mountpoint = iim.mountdmg(sparse_diskimage_path)
            if mountpoint:
                # install the product to the mounted sparseimage volume
                success = iim.install_product(
                    product_info[product_id]['DistributionPath'],
                    mountpoint)
                if not success:
                    print('Product installation failed.', file=sys.stderr)
                    iim.unmountdmg(mountpoint)
                    exit(-1)
                # add the seeding program xattr to the app if applicable
                # seeding_program = get_seeding_program(args.catalogurl)
                # if seeding_program:
                #    installer_app = find_installer_app(mountpoint)
                #    if installer_app:
                #        xattr.setxattr(installer_app, 'SeedProgram',
                #                       seeding_program)
                print('Product downloaded and installed to %s'
                      % sparse_diskimage_path)
                # Create a r/o compressed diskimage
                # containing the Install macOS app
                compressed_diskimagepath = os.path.join(
                    workdir, "output", volname + '.dmg')
                if os.path.exists(compressed_diskimagepath):
                    os.unlink(compressed_diskimagepath)
                app_path = iim.find_installer_app(mountpoint)
                if app_path:
                    iim.make_compressed_dmg(app_path, compressed_diskimagepath)
                # unmount sparseimage
                iim.unmountdmg(mountpoint)
                # delete sparseimage since we don't need it any longer
                os.unlink(sparse_diskimage_path)

                write_cache(workdir, product_id, product)


if __name__ == "__main__":
    main()
