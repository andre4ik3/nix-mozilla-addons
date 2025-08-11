import json
import json5
from urllib3 import PoolManager
from platform import system
from sys import argv

from updater.extras import get_extra_addons, to_sri_hash

USER_AGENT = f"NixMozillaAddons/1.0 ({system()}; +https://github.com/andre4ik3/nix-mozilla-addons)"

# Thunderbird doesn't support v5
API_VERSION = 4

# Mapping of products to their addon server.
ADDON_SERVER = {
    "firefox": "https://addons.mozilla.org/api",
    "thunderbird": "https://addons.thunderbird.net/api",
    "zotero": "https://example.com/placeholder/api",
}


def get_addon(http: PoolManager, api_base: str, addon_name: str) -> dict:
    """Fetches the data of an addon."""
    resp = http.request("GET", f"{api_base}/addons/addon/{addon_name}/")
    if resp.status != 200:
        raise Exception(f"Failed to fetch metadata for addon {addon_name}: HTTP {resp.status}")
    data = resp.json()

    version = data["current_version"]
    file = version["files"][0]

    return {
        "id": data["guid"],
        "alias": data["slug"],
        "version": version["version"],
        "file": {
            "url": file["url"],
            "hash": to_sri_hash(file["hash"]),
        },
        "passthru": {
            "file": file,
        },
    }


def update_addons_for_product(http: PoolManager, product: str, addons: list[str]):
    """Updates all addons for a particular product."""
    print(f"=> Updating addons for {product}")
    api_base = f"{ADDON_SERVER[product]}/v{API_VERSION}"

    try:
        with open(f"{product}.json", "r") as fp:
            data: dict = json.load(fp)
    except FileNotFoundError:
        data = {}

    for name in addons:
        print(f"Fetching {name}")
        try:
            data[name] = get_addon(http, api_base, name)
        except Exception as err:
            print(f"!! Failed to fetch addon {name}: {err}")

    # Merge with extra addons not found on Mozilla addons.
    data = {**data, **get_extra_addons(http, product)}

    with open(f"{product}.json", "w") as fp:
        json.dump(data, fp)


def main():
    http = PoolManager(headers={"User-Agent": USER_AGENT})

    with open(argv[1], "r") as fp:
        addon_list = json5.load(fp)

    for product in addon_list:
        update_addons_for_product(http, product, addon_list[product])


if __name__ == "__main__":
    main()
