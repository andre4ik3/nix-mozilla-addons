{
  description = "Access Mozilla addons from Nix";

  inputs = {
    nixpkgs.url = "https://nixpkgs.flake.andre4ik3.dev";
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
    eachSystem = systems: f: lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    sortedFiles = [ "addons.json5" "updater/extras.py" ];
  in
  {
    lib.supportedSystems = systems;

    overlays = rec {
      mozilla-addons = import ./overlay.nix data;
      default = mozilla-addons;
    };

    # `legacyPackages` is used instead of `packages`, because it's not a flat
    # package set, but rather grouped by product (i.e. `firefoxAddons.<...>`)
    legacyPackages = eachSystem systems (pkgs: self.overlays.mozilla-addons pkgs pkgs);

    packages = lib.warn ''
      nix-mozilla-addons: please use the legacyPackages output
    '' self.legacyPackages;

    devShells = eachSystem devSystems (pkgs: {
      default = pkgs.mkShell {
        packages = [ pkgs.python3 ];
      };
    });

    formatter = eachSystem devSystems (pkgs: pkgs.writeShellScriptBin "formatter" ''
      while [ ! -e "flake.nix" ]; do
        cd ..
        [ "$PWD" = "/" ] && exit 1
      done
      exec "${lib.getExe pkgs.keep-sorted}" "$@" ${lib.escapeShellArgs sortedFiles}
    '');

    checks = eachSystem devSystems (pkgs: {
      keep-sorted = pkgs.runCommand "formatter" { buildInputs = [ pkgs.keep-sorted ]; } ''
        cd "${self.outPath}"
        keep-sorted --mode lint ${lib.escapeShellArgs sortedFiles}
        touch "$out"
      '';
    });
  };
}
