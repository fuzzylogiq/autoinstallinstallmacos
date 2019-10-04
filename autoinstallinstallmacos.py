#!/usr/bin/python
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
        with open(cache_path, "r") as f:
            return plistlib.readPlist(f)


def write_cache(workdir, product_id, product):
    cache_path = os.path.join(workdir, ".cache.plist")
    products = {}
    if os.path.isfile(cache_path):
        with open(cache_path, "r") as f:
            products = plistlib.readPlist(f)
    products[product_id] = product
    with open(cache_path, "w") as f:
        plistlib.writePlist(products, f)


def main():
    su_catalog_url = iim.get_default_catalog()

    catalog = iim.download_and_parse_sucatalog(
        su_catalog_url, workdir)
    product_info = iim.os_installer_product_info(
        catalog, workdir)

    print(product_info)

    if not product_info:
        print("No macOS installer products found in the sucatalog.",
              file=sys.stderr)
        exit(-1)

    cached_products = check_cache(workdir)
    if cached_products:
        print("yes found cache!")
        print(cached_products)

    for product_id, product in product_info.items():
        if cached_products and product_id in cached_products.keys():
            print("Product %s is cached..." % product_id)
        else:
            print("Product %s is not in the cache, downloading..."
                  % product_id)
            iim.replicate_product(catalog, product_id,
                                  workdir, ignore_cache=True)
            write_cache(workdir, product_id, product)


if __name__ == "__main__":
    main()
