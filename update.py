# Update addons or something.
from base64 import b64encode
import json
import json5
from urllib3 import PoolManager
from platform import system
from datetime import datetime, timedelta, timezone

USER_AGENT = f"NixMozillaAddons/1.0 ({system()}; +https://github.com/andre4ik3/nix-mozilla-addons)"

# Thunderbird doesn't support v5
API_VERSION = 4

# Mapping of products to their addon server.
ADDON_SERVER = {
    "firefox": "https://addons.mozilla.org/api",
    "thunderbird": "https://addons.thunderbird.net/api"
}


# @dataclass
# class AddonData:
#     """Stores all data about a particular addon."""
#
#     # The timestamp of the last time the addon's version was successfully fetched.
#     fetch_last: datetime
#
#     # The timestamp when the addon should next be checked for version updates.
#     # fetch_next: datetime
#
#     # Global addon metadata retrieved from `/addons/{NAME}`.
#     metadata: dict
#
#     # The latest addon version retrieved from `/addons/{NAME}/versions`.
#     latest_version: dict


# def get_addon_metadata(http: PoolManager, api_base: str, addon_name: str) -> dict:
#     """Fetches the metadata of an addon."""
#     resp = http.request("GET", f"{api_base}/addons/addon/{addon_name}/")
#     if resp.status != 200:
#         raise Exception(f"Failed to fetch metadata for addon {addon_name}: HTTP {resp.status}")
#     return resp.json()
#
#
# def get_addon_versions(http: PoolManager, api_base: str, addon_name: str) -> dict:
#     """Fetches up to 25 last versions of an addon, in reverse chronological order."""
#     resp = http.request("GET", f"{api_base}/addons/addon/{addon_name}/versions/")
#     if resp.status != 200:
#         raise Exception(f"Failed to fetch latest version for addon {addon_name}: HTTP {resp.status}")
#     data = resp.json()
#     versions = data["results"]
#     versions = filter(lambda v: v["files"][0]["status"] == "public", versions)
#     versions = sorted(versions, key=lambda v: datetime.fromisoformat(v["files"][0]["created"]), reverse=True)
#     return versions


def to_sri_hash(data: str) -> str:
    """Converts a hash from an addon server to an SRI hash."""
    algorithm, data = data.split(":")
    data = bytes.fromhex(data)
    data = b64encode(data)
    data = data.decode("ascii")
    return f"{algorithm}-{data}".strip()


def calculate_fetch_cooldown(release_times: list[datetime]):
    """Calculates the next fetch cooldown based on the duration between recent releases."""
    differences = [x - y for x, y in zip(release_times[:-1], release_times[1:])]
    # TODO: some super fancy predictive algorithm, once there are enough addons that it starts to ratelimit
    return min(differences)


# def get_addon_metadata(http: PoolManager, api_base: str, addon_name: str) -> dict:
#     """Fetches the metadata of an addon."""
#     resp = http.request("GET", f"{api_base}/addons/addon/{addon_name}/")
#     if resp.status != 200:
#         raise Exception(f"Failed to fetch metadata for addon {addon_name}: HTTP {resp.status}")
#     return resp.json()

def get_addon(http: PoolManager, api_base: str, addon_name: str) -> dict:
    """Fetches the data of an addon."""
    # metadata = get_addon_metadata(http, api_base, addon_name)
    # versions = get_addon_versions(http, api_base, addon_name)

    # latest_version = versions[0]
    # release_times = [datetime.fromisoformat(x["files"][0]["created"]) for x in versions]
    # cooldown = calculate_fetch_cooldown(release_times)

    resp = http.request("GET", f"{api_base}/addons/addon/{addon_name}/")
    if resp.status != 200:
        raise Exception(f"Failed to fetch metadata for addon {addon_name}: HTTP {resp.status}")
    data = resp.json()

    version = data["current_version"]
    file = version["files"][0]

    return {
        "id": data["guid"],
        "alias": data["slug"],
        "lastFetch": datetime.now(timezone.utc).isoformat(),
        "version": version["version"],
        "file": {
            **file,
            "hash": to_sri_hash(file["hash"]),
        },
    }


def update_addons_for_product(http: PoolManager, product: str, addons: list[str]):
    """Updates all addons for a particular product."""
    print(f"=> Updating addons for {product}")

    api_base = f"{ADDON_SERVER[product]}/v{API_VERSION}"

    with open(f"addons/{product}.json", "r") as fp:
        data: dict = json.load(fp)

    for name in addons:
        now = datetime.now(timezone.utc)
        last_fetch = datetime.fromtimestamp(0, timezone.utc)

        if name in data:
            last_fetch = datetime.fromisoformat(data[name]["lastFetch"])

        # if now >= last_fetch + timedelta(days=7):
        if True:
            print(f"Fetching {name}")
            try:
                data[name] = get_addon(http, api_base, name)
            except Exception as err:
                print(f"!! Failed to fetch addon {name}: {err}")

    with open(f"addons/{product}.json", "w") as fp:
        json.dump(data, fp)


def main():
    http = PoolManager(headers={"User-Agent": USER_AGENT})

    with open("addon-list.json5", "r") as fp:
        addon_list = json5.load(fp)

    for product in addon_list:
        update_addons_for_product(http, product, addon_list[product])


if __name__ == "__main__":
    main()
