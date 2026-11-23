# roccat

GTK-Anwendung für die Beleuchtung der ROCCAT Magma und der kabelgebundenen ROCCAT Kone Pro unter Linux Mint 22.x (x86-64).

## Deutsch

- OpenRGB erkennt die verfügbaren Modi, Farbbereiche und Regler. Änderungen werden erst mit **Auf Gerät anwenden** gesendet.
- Farbprofile lassen sich lokal verwalten und als JSON importieren oder exportieren.
- Das DEB richtet den Desktop-Starter und einen lokalen OpenRGB-SDK-Systemdienst auf Port 6742 ein. Der Dienst startet beim Hochfahren.
- Tastaturlayout und Tastenkürzel werden in Linux Mint eingestellt. roccat konzentriert sich auf Beleuchtung.

[Installation und Entfernung](packaging/Installation.md) · [Hilfe](hilfe/hilfe-de.html) · [Dogtruck](https://dogtruck.eu/)

## English

roccat controls lighting on the ROCCAT Magma and wired ROCCAT Kone Pro on Linux Mint 22.x (x86-64). It uses the modes and controls reported by OpenRGB and sends changes when you select **Apply to device**. Color profiles can be stored locally and exchanged as JSON.

The DEB installs a desktop launcher and a local OpenRGB SDK service on port 6742. The service starts at boot. Keyboard layouts and shortcuts are managed in Linux Mint.

[Help](hilfe/hilfe-en.html) · [Dogtruck](https://dogtruck.eu/)

## Build

Download the original OpenRGB 1.1 x86-64 AppImage from its [upstream release](https://codeberg.org/OpenRGB/OpenRGB/releases/tag/release_1.1). Set `OPENRGB_APPIMAGE` to its path and run `./packaging/build-deb.sh`. The build verifies its SHA-256 digest. The upstream SDK source and license notices are documented in [packaging/copyright](packaging/copyright). roccat is an independent project. ROCCAT branding identifies the supported hardware.
