{
  description = "Access Mozilla addons from Nix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/release-25.05";
    flake-compat.url = "github:nix-community/flake-compat";

    data = {
      url = "github:andre4ik3/nix-mozilla-addons/data";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, data, ... }: let
    inherit (nixpkgs) lib;
    systems = lib.systems.flakeExposed;
    devSystems = [ "aarch64-darwin" "aarch64-linux" "x86_64-darwin" "x86_64-linux" ];
  in {
    lib.supportedSystems = systems;

    overlays = rec {
      mozilla-addons = import ./overlay.nix data;
      default = mozilla-addons;
    };

    packages = lib.genAttrs systems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in self.overlays.mozilla-addons pkgs pkgs);

    devShells = lib.genAttrs devSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      default = pkgs.mkShell {
        packages = with pkgs; [
          keep-sorted
          python3
        ];
      };
    });
  };
}
