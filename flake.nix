{
  description = "Access browser addons from Nix";

  inputs = {
    nixpkgs.url = "https://nixpkgs.flake.andre4ik3.dev";

    data = {
      url = "github:andre4ik3/nix-browser-addons/data";
      flake = false;
    };

    treefmt = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, data, ... }@inputs: let
    inherit (nixpkgs) lib;
    systems = lib.systems.flakeExposed;
    devSystems = [ "aarch64-darwin" "aarch64-linux" "x86_64-darwin" "x86_64-linux" ];
    eachSystem = systems: f: lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    treefmt = pkgs: (inputs.treefmt.lib.evalModule pkgs ./treefmt.nix);
  in
  {
    lib.supportedSystems = systems;

    overlays = rec {
      mozilla-addons = lib.warn "nix-mozilla-addons has been renamed to nix-browser-addons" browser-addons;
      browser-addons = import ./overlay.nix data;
      default = browser-addons;
    };

    # `legacyPackages` is used instead of `packages`, because it's not a flat
    # package set, but rather grouped by product (i.e. `firefoxAddons.<...>`)
    legacyPackages = eachSystem systems (pkgs: self.overlays.browser-addons pkgs pkgs);

    packages = lib.warn ''
      nix-browser-addons: please use the legacyPackages output
    '' self.legacyPackages;

    devShells = eachSystem devSystems (pkgs: {
      default = pkgs.mkShell {
        packages = [ pkgs.deno ];
      };
    });

    formatter = eachSystem devSystems (pkgs: (treefmt pkgs).config.build.wrapper);
    checks = eachSystem devSystems (pkgs: {
      treefmt = (treefmt pkgs).config.build.check self;
    });
  };
}
