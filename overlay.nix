# from flake.nix:
data:

# from nixpkgs/when used as an overlay:
final: prev:

let
  inherit (final) lib fetchurl;

  mkAddonPackage = pname: addon: fetchurl {
    inherit pname;
    inherit (addon) version passthru;
    inherit (addon.file) url hash;
  };

  addonsForProduct = product: let
    addons = lib.importJSON "${data}/${product}.json";
  in lib.mapAttrs (mkAddonPackage) addons;
in

{
  firefoxAddons = addonsForProduct "firefox";
  thunderbirdAddons = addonsForProduct "thunderbird";
  zoteroAddons = addonsForProduct "zotero";
}
