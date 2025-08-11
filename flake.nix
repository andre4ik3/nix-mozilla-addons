{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/release-25.05";

    data = {
      url = "github:andre4ik3/nix-mozilla-addons/data";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, data, ... }: let
    inherit (nixpkgs) lib;
    devSystems = [ "aarch64-darwin" "aarch64-linux" "x86_64-darwin" "x86_64-linux" ];
  in {
    overlays = rec {
      mozilla-addons = import ./overlay.nix data;
      default = mozilla-addons;
    };

    packages = lib.genAttrs lib.systems.flakeExposed (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in self.overlays.mozilla-addons pkgs pkgs);

    devShells = lib.genAttrs devSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      default = pkgs.mkShell {
        packages = [ pkgs.python3 ];
      };
    });
  };
}
