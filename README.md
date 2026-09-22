Nix Browser Addons
==================

Manage addons using Nix for:

- [Chromium] (`pkgs.chromiumExtensions`)
- [Firefox] (`pkgs.firefoxAddons`)
- [Thunderbird] (`pkgs.thunderbirdAddons`)
- [Zotero] (`pkgs.zoteroAddons`)

**Why?**

- Keep addons versioned together with your system
- Choose and pin your addon versions, only updating them when you need
- Instant forced addon installation with enterprise policies (instead of having to wait for background download)
- Identically easy deployment for addons both on and off the official Chromium/Mozilla addon server
- Deploy addons *offline* as part of a system image

See [`addons.ts`](./src/addons.ts) for the list of currently supported addons.

Adding a new addon is as simple as adding a single line to that file.

Addons are automatically updated daily using GitHub actions using the [Updater](#updater).

Usage
-----

The addon data files are stored in a separate branch from the code (to allow pinning the addon versions separately from the code.

### With Flakes

```nix
{
  inputs = {
    # ... other stuff ...

    browser-addons = {
      url = "github:andre4ik3/nix-browser-addons";
      inputs.nixpkgs.follows = "nixpkgs";
      # the below input controls the actual addon data, auto-updated daily
      # update your version pin using `nix flake update browser-addons/data`
      inputs.data.url = "github:andre4ik3/nix-browser-addons/data";
    };

    # ... other stuff ...
  };

  outputs = { browser-addons, nixpkgs, ... }: {
    nixosConfigurations.exampleSystem = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ./some-module.nix
        # ... other stuff ...
        {
          nixpkgs.overlays = [ browser-addons.overlays.default ];
        }
        # ... other stuff ...
      ];
    };
  };
}
```

### Without Flakes

The main entry point is `overlay.nix`, which is a Nixpkgs overlay, but it also needs the `data` branch passed as an argument.
You need to fetch both branches and pass the `data` branch's store path to `overlay.nix`, like so:

```nix
let
  base = "https://github.com/andre4ik3/nix-browser-addons/archive/refs/heads";
  master = builtins.fetchTarball { url = "${base}/master.zip"; };
  data = builtins.fetchTarball { url = "${base}/data.zip"; };
in
import "${master}/overlay.nix" data
```

Configuration
-------------

This repo doesn't provide facilities to actually *install* the extensions.

While I don't currently provide exact modules, I can at least provide some per-browser examples:

### Chromium

> [!CAUTION]
> On macOS, this only works for *unbranded* Chromium, Ungoogled Chromium, and Helium.
> For Google Chrome and other branded browsers, **it will only work on Linux.**

The gist is that you need to create an `External Extensions` directory in Chromium's user folder.

| Platform | System-wide                             | User-Specific                            |
| -------- | --------------------------------------- | ---------------------------------------- |
| Linux    | `$XDG_DATA_DIRS/$browser`               | `$XDG_CONFIG_HOME/$browser`              |
| macOS    | `/Library/Application Support/$browser` | `~/Library/Application Support/$browser` |

`$browser` is not necessarily the package name, for example for Helium it's `net.imput.helium`.
It might also be different per-platform, e.g. `Google/Chrome` on macOS and `google-chrome` on Linux.

You can generate the whole directory trivially with Nix:

```nix
let
  json = pkgs.formats.json { };
  extensions = with pkgs.chromiumExtensions; [
    ublock-origin
    anubis-bypass
    keepassxc-browser
    plasma-integration
    # any other extension you want...
  ];
in
pkgs.linkFarm "external-extensions" (map (extension: rec {
  name = "${extension.passthru.id}.json";
  path = json.generate name {
    external_crx = extension;
    external_version = extension.version;
  };
}) extensions)
```

Then, you need to get that directory to the appropriate path for your browser:

- On Home Manager, you can use `home.file`.
- On NixOS, you could probably create a `runCommandLocal` that symlinks the directory from the snippet above (or similar) into `$out/share/$browser/"External Extensions"` or so.
- On Nix-Darwin, it would probably have to be an activation script to `mkdir -p` the directory then `ln -sf`.

See also [official documentation](https://developer.chrome.com/docs/extensions/how-to/distribute/install-extensions#preferences) on external extension installation.

### Mozilla (Firefox, Thunderbird)

```nix
{ pkgs, ... }:

let
  policies = with pkgs.firefoxAddons; {
    ExtensionSettings = {
      ${ublock-origin.id} = {
        install_url = "file://${ublock-origin}";
        installation_mode = "force_installed";
        default_area = "menupanel";
        private_browsing = true;
      };
    };
    "3rdparty".extensions = {
      ${ublock-origin.id} = {
        toOverwrite.filterLists = [
          "user-filters"
          "ublock-filters"
          "ublock-badware"
          "ublock-privacy"
          "ublock-quick-fixes"
          "ublock-unbreak"
          "easylist"
          "easyprivacy"
          "urlhaus-1"
          "plowe-0"
          "fanboy-cookiemonster"
          "ublock-cookies-easylist"
          "fanboy-social"
          "easylist-chat"
          "easylist-newsletters"
          "easylist-notifications"
          "easylist-annoyances"
        ];
      };
    };
  };

  package = pkgs.firefox.override {
    extraPolicies = policies;
  };
in

{
  # for Darwin
  environment.systemPackages = [ package ];

  # for NixOS
  programs.firefox = {
    enable = true;
    inherit package policies;
  };
}
```

Updater
-------

The extension updater is considered an implementation detail. It runs every day automatically and pushes updates to the `data` branch in this repo.

Currently, the updater is implemented in Deno, with the Zod and Effect libraries. Before it was in Python with Requests.

Fetching an update is tried up to 3 times for each extension, and extensions that fail to update will keep their old version.

You can run the updater locally yourself to generate the extension data with:

```sh
# generates addons/{chromium,firefox,thunderbird}.json
# if the files already exist, they will be partially updated
deno run -A ./src/main.ts addons
```

[Chromium]: https://chromewebstore.google.com/
[Firefox]: https://addons.mozilla.org/en-US/firefox/
[Thunderbird]: https://addons.thunderbird.net/en-US/thunderbird/
[Zotero]: https://www.zotero.org/support/plugins
