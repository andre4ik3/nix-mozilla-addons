from base64 import b64encode
from urllib3 import PoolManager
from re import search


def to_sri_hash(data: str) -> str:
    """Converts a hash from an addon server to an SRI hash."""
    algorithm, data = data.split(":")
    data = bytes.fromhex(data)
    data = b64encode(data)
    data = data.decode("ascii")
    return f"{algorithm}-{data}".strip()


def get_from_github(http: PoolManager, *, name: str, id: str, owner: str, repo: str) -> dict:
    """Fetches an addon from GitHub releases."""
    resp = http.request("GET", f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
    if resp.status != 200:
        raise Exception(f"Failed to fetch metadata for addon {name}: HTTP {resp.status}")
    data = resp.json()
    version = data["tag_name"].removeprefix("v")
    file = data["assets"][0]
    assert file["digest"]
    return {
        "name": name,
        "version": version,
        "file": {
            "url": file["browser_download_url"],
            "hash": to_sri_hash(file["digest"]),
        },
        "passthru": {
            "id": id,
            "alias": name,
        },
    }


def get_from_update_url(http: PoolManager, *, name: str, id: str, url: str) -> dict:
    """Fetches an addon from its update URL."""
    resp = http.request("GET", url)
    if resp.status != 200:
        raise Exception(f"Failed to fetch metadata for addon {name}: HTTP {resp.status}")
    data = resp.json()["addons"][id]
    file = data[-1]
    return {
        "name": name,
        "version": file["version"],
        "file": {
            "url": file["update_link"],
            "hash": to_sri_hash(file["update_hash"]),
        },
        "passthru": {
            "id": id,
            "alias": name,
        },
    }


def bpc_get_hash(hashes: str, filename: str) -> str:
    """Scans the Bypass Paywalls Clean hashes file to extract a particular file's hash from it."""
    hashes = hashes.split("\n==================================================")
    entry = filter(lambda x: filename in x, hashes)
    entry = list(entry)[0]
    data = search("\w{64}", entry)[0]
    return to_sri_hash(f"sha256:{data}")


def get_firefox_bpc(http: PoolManager) -> dict:
    """Fetches the Bypass Paywalls Clean addon for Firefox."""
    resp = http.request("GET", "https://gitflic.ru/project/magnolia1234/bpc_updates/blob/raw?file=updates.json")
    if resp.status != 200:
        raise Exception(f"Failed to fetch metadata for addon {name}: HTTP {resp.status}")
    data = resp.json()
    file = data["addons"]["magnolia@12.34"]["updates"][-1]
    filename = file["update_link"].split("?file=")[-1]

    hashes = http.request("GET", "https://gitflic.ru/project/magnolia1234/bpc_uploads/blob/raw?file=release-hashes.txt")
    if hashes.status != 200:
        raise Exception(f"Failed to fetch metadata for addon {name}: HTTP {resp.status}")

    return {
        "name": "bypass-paywalls-clean",
        "version": file["version"],
        "file": {
            "url": file["update_link"],
            "hash": bpc_get_hash(hashes.data.decode("utf-8"), filename),
        },
        "passthru": {
            "id": "magnolia@12.34",
            "alias": "bypass-paywalls-clean",
        },
    }


# Mapping of extension package names to their fetchers.
FETCHERS = {
    "firefox": {
        "bypass-paywalls-clean": lambda http: get_firefox_bpc(http),
        "zotero-connector": lambda http: get_from_update_url(
            http, name="zotero-connector", id="zotero@chnm.gmu.edu",
            url="https://www.zotero.org/download/connector/firefox/release/updates.json"
        )
    },
    "thunderbird": {},
    "zotero": {
        "attachment-scanner": lambda http: get_from_github(
            http, name="attachment-scanner", id="attachmentscanner@changlab.um.edu.mo",
            owner="SciImage", repo="zotero-attachment-scanner"
        ),
        "better-bibtex": lambda http: get_from_github(
            http, name="better-bibtex", id="better-bibtex@iris-advies.com",
            owner="retorquere", repo="zotero-better-bibtex"
        ),
        "folder-import": lambda http: get_from_github(
            http, name="folder-import", id="folder-import@iris-advies.com",
            owner="retorquere", repo="zotero-folder-import"
        ),
        "ocr": lambda http: get_from_github(
            http, name="ocr", id="zotero-ocr@bib.uni-mannheim.de",
            owner="UB-Mannheim", repo="zotero-ocr"
        ),
        "open-pdf": lambda http: get_from_github(
            http, name="open-pdf", id="open-pdf@iris-advies.com",
            owner="retorquere", repo="zotero-open-pdf"
        ),
        "pmcid-fetcher": lambda http: get_from_github(
            http, name="pmcid-fetcher", id="pmcid-fetcher@iris-advies.com",
            owner="retorquere", repo="zotero-pmcid-fetcher"
        ),
        "pubpeer": lambda http: get_from_github(
            http, name="pubpeer", id="pubpeer@pubpeer.com",
            owner="PubPeerFoundation", repo="pubpeer_zotero_plugin"
        ),
        "scite": lambda http: get_from_github(
            http, name="scite", id="scite-zotero-plugin@scite.ai",
            owner="scitedotai", repo="scite-zotero-plugin"
        ),
    },
}


def get_extra_addons(http: PoolManager, product: str, data: dict) -> dict:
    """Returns extra addons for a product that aren't found on Mozilla's addons servers."""
    fetchers = FETCHERS[product]
    for name, fetcher in fetchers.items():
        try:
            print(f"Fetching {name}")
            data[name] = fetcher(http)
        except Exception as err:
            print(f"!! Failed to fetch addon {name}: {err}")
    return data
