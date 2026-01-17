import json
from urllib.parse import urlencode, urlsplit, parse_qs

from urllib3 import PoolManager

from updater.extras import get_extra_addons, parse_chromium_extension

BASE_URL = "https://services.helium.imput.net/ext/?"


def make_url(extension_id: str) -> str:
    return BASE_URL + urlencode({
        "x": urlencode({
            "id": extension_id
        }) + "&uc"  # required to return XML data or something
    })


def get_extension(http: PoolManager, extension_id: str, name: str):
    url = make_url(extension_id)
    resp = http.request("GET", url)
    if resp.status != 200:
        raise Exception(f"HTTP {resp.status}")
    return parse_chromium_extension(name, resp.data)


def unproxy(url: str) -> str:
    components = urlsplit(url)
    query = parse_qs(components.query)
    return query["url"][0]


def update_addons_for_chromium(http: PoolManager, addons: dict[str, str]):
    print(f"=> Updating addons for Chromium")
    try:
        with open(f"chromium.json", "r") as fp:
            data = json.load(fp)
    except FileNotFoundError as err:
        data = {}

    for name in list(data.keys()):
        if name not in addons:
            del data[name]

    for name, addon_id in addons.items():
        print(f"Fetching {name}")
        try:
            data[name] = get_extension(http, addon_id, name)
        except Exception as err:
            print(f"!! Failed to fetch addon {name}: {err}")

    # Merge with extra addons not found on the Chrome Web Store.
    data = {**data, **get_extra_addons(http, "chromium", data)}

    with open(f"chromium.json", "w") as fp:
        json.dump(data, fp)
