#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
cd "$root"
arch=amd64
[ "$(dpkg --print-architecture)" = "$arch" ] || { echo "Build requires amd64." >&2; exit 1; }
image="${OPENRGB_APPIMAGE:-$HOME/.cache/roccat/OpenRGB-1.1.AppImage}"
printf '%s  %s\n' d556c2273b0ef863dbee7ffdb438304b382add5d685c93c60758b42de3b0268d "$image" | sha256sum -c -
version=$(cat VERSION)
dest=$(mktemp -d)
trap 'rm -rf -- "$dest"' EXIT
base="$dest/usr/lib/roccat"
install -d "$dest/DEBIAN" "$base" "$base/system" "$base/referenzen/original/openrgb-python"
cp -R src .basis .basisbilder bilder hilfe VERSION "$base/"
find "$base" -type d -name __pycache__ -prune -exec rm -rf {} +
install -m 0755 "$image" "$base/system/OpenRGB.AppImage"
install -m 0755 packaging/openrgb-service packaging/lighting-autostart "$base/system/"
install -m 0644 -D packaging/roccat-profil-start.service "$dest/usr/lib/systemd/user/roccat-profil-start.service"
install -m 0755 packaging/desktop-starter "$base/system/"
install -m 0644 packaging/OpenRGB.json "$base/system/"
cp -R referenzen/original/openrgb-python/openrgb referenzen/original/openrgb-python/LICENSE.md \
    "$base/referenzen/original/openrgb-python/"
find "$base/referenzen" -type d -name __pycache__ -prune -exec rm -rf {} +
install -m 0755 -D packaging/roccat "$dest/usr/bin/roccat"
ln -s ../lib/roccat/system/lighting-autostart "$dest/usr/bin/roccat-lichtdienst"
install -m 0755 packaging/roccat.desktop "$base/roccat.desktop"
install -d "$dest/usr/share/applications"
ln -s ../../lib/roccat/roccat.desktop "$dest/usr/share/applications/roccat.desktop"
install -m 0644 -D packaging/roccat-openrgb.service "$dest/usr/lib/systemd/system/roccat-openrgb.service"
install -m 0644 -D packaging/roccat-openrgb.conf "$dest/usr/lib/sysusers.d/roccat-openrgb.conf"
install -m 0644 -D packaging/72-roccat-openrgb.rules "$dest/usr/lib/udev/rules.d/72-roccat-openrgb.rules"
install -m 0644 -D packaging/copyright "$dest/usr/share/doc/roccat/copyright"
install -m 0644 -D packaging/Installation.md "$dest/usr/share/doc/roccat/Installation.md"
install -m 0755 packaging/postinst packaging/prerm "$dest/DEBIAN/"
installed_size=$(du -sk --exclude=DEBIAN "$dest" | cut -f1)
cat > "$dest/DEBIAN/control" <<CONTROL
Package: roccat
Version: $version
Architecture: $arch
Maintainer: Josef Lehner
Section: utils
Priority: optional
Installed-Size: $installed_size
Depends: python3 (>= 3.10), python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, gir1.2-webkit2-4.1, librsvg2-common, systemd, udev, init-system-helpers, xdg-user-dirs, libglib2.0-bin, util-linux, adduser, libc6, libstdc++6, libgcc-s1, libegl1, libglx0, libglvnd0, libopengl0, libx11-6, libxcb1, libexpat1, libfontconfig1, libfreetype6, libharfbuzz0b, libusb-1.0-0, zlib1g
Description: Lighting controls for ROCCAT Magma and Kone Pro
 GTK application for USB lighting and local color profiles. Includes the OpenRGB
 SDK server as a system service listening on localhost only.
CONTROL
install -d dist
dpkg-deb --root-owner-group --build "$dest" "dist/roccat_${version}_${arch}.deb"
