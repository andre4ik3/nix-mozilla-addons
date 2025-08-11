# from flake.nix:
data:

# from nixpkgs/when used as an overlay:
final: prev:

let
  inherit (final) lib fetchurl;

  mkAddonPackage = addon: fetchurl {
    # name = "${addon.alias}-${addon.version}.xpi";
    pname = addon.alias;
    inherit (addon) version passthru;
    inherit (addon.file) url hash;
  };

  addonsForProduct = product: let
    addons = lib.attrValues (lib.importJSON "${data}/${product}.json");
    mkAddonPackages = addon: let
      package = mkAddonPackage addon;
    in [
      (lib.nameValuePair addon.id package)
      (lib.nameValuePair addon.alias package)
    ];
    addonPackages = lib.map mkAddonPackages addons;
  in lib.listToAttrs (lib.concatLists addonPackages);
in

{
  firefoxAddons = addonsForProduct "firefox";
  thunderbirdAddons = addonsForProduct "thunderbird";
}
