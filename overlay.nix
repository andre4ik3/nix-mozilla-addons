# from flake.nix:
data:

# from nixpkgs/when used as an overlay:
final: prev:

let
  inherit (final) lib fetchurl;

  mkAddonPackage = addon: fetchurl {
    # name = "${addon.alias}-${addon.version}.xpi";
    pname = addon.name;
    inherit (addon) version;
    inherit (addon.file) url hash;
    passthru = {
      inherit (addon) id alias;
    } // addon.passthru;
  };

  addonsForProduct = product: let
    addons = lib.attrValues (lib.importJSON "${data}/${product}.json");
  in lib.mapAttrValues (name: mkAddonPackage) addons;
in

{
  firefoxAddons = addonsForProduct "firefox";
  thunderbirdAddons = addonsForProduct "thunderbird";
  zoteroAddons = addonsForProduct "zotero";
}
