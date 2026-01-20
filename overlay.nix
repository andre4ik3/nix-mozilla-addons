# from flake.nix:
data:

# from nixpkgs/when used as an overlay:
final: prev:

let
  inherit (final) lib fetchurl;

  mkAddonPackage = ext: pname: addon: fetchurl {
    name = "${pname}-${addon.version}.${ext}";
    inherit (addon) passthru;
    inherit (addon.file) url hash;
  };

  addonsForProduct = product: let
    extension = if product == "chromium" then "crx" else "xpi";
    mkAddonPackage' = mkAddonPackage extension;
    addons = lib.importJSON "${data}/${product}.json";
  in lib.mapAttrs mkAddonPackage' addons;
in

{
  firefoxAddons = addonsForProduct "firefox";
  thunderbirdAddons = addonsForProduct "thunderbird";
  zoteroAddons = addonsForProduct "zotero";
  chromiumExtensions = addonsForProduct "chromium";
}
