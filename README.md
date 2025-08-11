Nix Mozilla Addons
==================

Manage addons for Mozilla-based programs ([Firefox], [Thunderbird], and [Zotero]) using Nix.

**Why?**

- Keep addons versioned together with your system
- Choose and pin your addon versions, only updating them when you need
- Instant forced addon installation with enterprise policies (instead of having to wait for background download)
- Identically easy deployment for addons both on and off the official Mozilla addon server
- Deploy addons *offline* as part of a system image

See [`addons.json5`](./addons.json5) for the list of currently supported addons. Adding a new addon is as simple as
adding a single line to that file (unless it's not on the Mozilla addon server). Zotero and other extensions can be
seen in [`extras.py`](./updater/extras.py).

Extensions are automatically updated daily using GitHub actions.

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

    mozilla-addons = {
      url = "github:andre4ik3/nix-mozilla-addons";
      inputs.nixpkgs.follows = "nixpkgs";
      # the below input controls the actual addon data, auto-updated daily
      # update your version pin using `nix flake update mozilla-addons/data`
      inputs.data.url = "github:andre4ik3/nix-mozilla-addons/data";
    };

    # ... other stuff ...
  };

  outputs = { mozilla-addons, nixpkgs, ... }: {
    nixosConfigurations.exampleSystem = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ./some-module.nix
        # ... other stuff ...
        {
          nixpkgs.overlays = [ mozilla-addons.overlays.default ];
        }
        # ... other stuff ...
      ];
    };
  };
}
```
