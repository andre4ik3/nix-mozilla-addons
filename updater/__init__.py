import json5
from urllib3 import PoolManager
from platform import system
from sys import argv

from updater.chromium import update_addons_for_chromium
from updater.extras import get_extra_addons, to_sri_hash_prefixed
from updater.mozilla import update_addons_for_mozilla_product

USER_AGENT = f"NixMozillaAddons/1.0 ({system()}; +https://github.com/andre4ik3/nix-mozilla-addons)"

def main():
    http = PoolManager(headers={"User-Agent": USER_AGENT})

    with open(argv[1], "r") as fp:
        addon_list = json5.load(fp)

    for product in addon_list:
        if product == "chromium":
            update_addons_for_chromium(http, addon_list[product])
        else:
            update_addons_for_mozilla_product(http, product, addon_list[product])


if __name__ == "__main__":
    main()
