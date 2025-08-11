Nix Mozilla Addons
==================

Automatically updated flake that provides selected addons for the following:

- [Firefox]
  - Firefox Multi-Account Containers
  - JShelter
  - NoScript
  - uBlock Origin
  - Bitwarden Password Manager
  - KeePassXC-Browser
  - Plasma Integration
  - BetterTTV
  - SponsorBlock
  - Adaptive Tab Bar Color
  - Catppuccin for Web File Explorer
  - Dark Reader
  - Stylus
  - Tampermonkey
  - User Agent String Switcher
  - React Developer Tools
  - Vue.js Devtools
  - Bypass Paywalls Clean
- [Thunderbird]
  - ImportExportTools NG
- [Zotero]
  - Better BibTeX

[Firefox]: https://addons.mozilla.org/en-US/firefox/
[Thunderbird]: https://addons.thunderbird.net/en-US/thunderbird/
[Zotero]: https://www.zotero.org/support/plugins

Usage
-----

The addon data files are stored in a separate branch from the code (to allow
pinning the addon versions separately from the code):

```nix
{
  inputs = {
    # ... other stuff ...

    # auto daily-updated data from addon servers
    mozilla-addons = {
      url = "github:andre4ik3/nix-mozilla-addons/data";
      flake = false;
    };

    nix-mozilla-addons = {
      url = "github:andre4ik3/nix-mozilla-addons";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.data.follows = "mozilla-addons";
    };

    # ... other stuff ...
  };

  outputs = { nix-mozilla-addons, nixpkgs, ... }: {
    nixosConfigurations.exampleSystem = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ./some-module.nix
        # ... other stuff ...
        {
          nixpkgs.overlays = [ nix-mozilla-addons.overlays.default ];
        }
        # ... other stuff ...
      ];
    };
  };
}
```
