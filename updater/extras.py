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
    print(f"Fetching {name}")
    resp = http.request("GET", f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
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


def bpc_get_hash(hashes: str, filename: str) -> str:
    """Scans the Bypass Paywalls Clean hashes file to extract a particular file's hash from it."""
    hashes = hashes.split("\n==================================================")
    entry = filter(lambda x: filename in x, hashes)
    entry = list(entry)[0]
    data = search("\w{64}", entry)[0]
    return to_sri_hash(f"sha256:{data}")


def get_firefox_bpc(http: PoolManager) -> dict:
    """Fetches the Bypass Paywalls Clean addon for Firefox."""
    print(f"Fetching bypass-paywalls-clean")
    resp = http.request("GET", "https://gitflic.ru/project/magnolia1234/bpc_updates/blob/raw?file=updates.json")
    data = resp.json()
    file = data["addons"]["magnolia@12.34"]["updates"][0]
    filename = file["update_link"].split("?file=")[-1]

    hashes = http.request("GET", "https://gitflic.ru/project/magnolia1234/bpc_uploads/blob/raw?file=release-hashes.txt")
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


def get_extra_addons(http: PoolManager, product: str) -> dict:
    """Returns extra addons for a product that aren't found on Mozilla's addons servers."""
    if product == "firefox":
        return {
            "bypass-paywalls-clean": get_firefox_bpc(http),
        }
    elif product == "zotero":
        return {
            # TODO: the commented addons don't have SHA256 digests on the releases???
            # "attachment-scanner": get_from_github(
            #     http, name="attachment-scanner", id="attachmentscanner@changlab.um.edu.mo",
            #     owner="SciImage", repo="zotero-attachment-scanner"
            # ),
            "better-bibtex": get_from_github(
                http, name="better-bibtex", id="better-bibtex@iris-advies.com",
                owner="retorquere", repo="zotero-better-bibtex"
            ),
            # "folder-import": get_from_github(
            #     http, name="folder-import", id="folder-import@iris-advies.com",
            #     owner="retorquere", repo="zotero-folder-import"
            # ),
            # "ocr": get_from_github(
            #     http, name="ocr", id="zotero-ocr@bib.uni-mannheim.de",
            #     owner="UB-Mannheim", repo="zotero-ocr"
            # ),
            # "open-pdf": get_from_github(
            #     http, name="open-pdf", id="open-pdf@iris-advies.com",
            #     owner="retorquere", repo="zotero-open-pdf"
            # ),
            "pmcid-fetcher": get_from_github(
                http, name="pmcid-fetcher", id="pmcid-fetcher@iris-advies.com",
                owner="retorquere", repo="zotero-pmcid-fetcher"
            ),
            # "pubpeer": get_from_github(
            #     http, name="pubpeer", id="pubpeer@pubpeer.com",
            #     owner="PubPeerFoundation", repo="pubpeer_zotero_plugin"
            # ),
            # "scite": get_from_github(
            #     http, name="scite", id="scite-zotero-plugin@scite.ai",
            #     owner="scitedotai", repo="scite-zotero-plugin"
            # ),
        }
    else:
        return {}
