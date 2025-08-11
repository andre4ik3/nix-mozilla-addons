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


def bpc_get_hash(hashes: str, filename: str) -> str:
    """Scans the Bypass Paywalls Clean hashes file to extract a particular file's hash from it."""
    hashes = hashes.split("\n==================================================")
    print(filename)
    entry = filter(lambda x: filename in x, hashes)
    entry = list(entry)[0]
    data = search("\w{64}", entry)[0]
    return to_sri_hash(f"sha256:{data}")


def get_firefox_bpc(http: PoolManager) -> dict:
    """Fetches the Bypass Paywalls Clean addon for Firefox."""
    resp = http.request("GET", "https://gitflic.ru/project/magnolia1234/bpc_updates/blob/raw?file=updates.json")
    data = resp.json()
    file = data["addons"]["magnolia@12.34"]["updates"][0]
    filename = file["update_link"].split("?file=")[-1]

    hashes = http.request("GET", "https://gitflic.ru/project/magnolia1234/bpc_uploads/blob/raw?file=release-hashes.txt")
    return {
        "id": "magnolia@12.34",
        "alias": "bypass-paywalls-clean",
        "version": file["version"],
        "file": {
            "url": file["update_link"],
            "hash": bpc_get_hash(hashes.data.decode("utf-8"), filename),
        },
        "passthru": {
            "file": file,
        },
    }


def get_zotero_better_bibtex(http: PoolManager) -> dict:
    """Fetches the Better BibTeX addon for Zotero."""
    resp = http.request("GET", "https://api.github.com/repos/retorquere/zotero-better-bibtex/releases/latest")
    data = resp.json()
    version = data["tag_name"].removeprefix("v")
    file = data["assets"][0]
    return {
        "id": "better-bibtex@iris-advies.com",
        "alias": "better-bibtex",
        "version": version,
        "file": {
            "url": file["browser_download_url"],
            "hash": to_sri_hash(file["digest"]),
        },
        "passthru": {
            "file": file,
        },
    }


def get_extra_addons(http: PoolManager, product: str) -> dict:
    """Returns extra addons for a product that aren't found on Mozilla's addons servers."""
    if product == "firefox":
        return {
            "magnolia@12.34": get_firefox_bpc(http),
        }
    elif product == "zotero":
        return {
            "better-bibtex@iris-advies.com": get_zotero_better_bibtex(http),
        }
    else:
        return {}
