# roccat als Debian-Paket installieren

Das Paket ist für Linux Mint 22.x mit x86-64 und systemd vorgesehen.

1. Wenn die ältere Benutzerversion des OpenRGB-Dienstes läuft, vor der Paketinstallation als bisheriger Benutzer `systemctl --user disable --now roccat-openrgb.service` ausführen. Für einen temporären Dienst genügt `systemctl --user stop roccat-openrgb.service`. Ein paralleler Dienst belegt sonst denselben Port.
2. Im Ordner mit dem DEB `sudo apt install ./roccat_0.1.3_amd64.deb` ausführen. APT installiert die angeführten Systembibliotheken. OpenRGB und das Python-SDK sind im Paket enthalten.
3. `systemctl is-active roccat-openrgb.service` prüft den Betrieb. Der Systemdienst startet bei jedem Systemstart vor der Desktop-Anmeldung und lauscht nur auf 127.0.0.1:6742.
4. `roccat` öffnet die Oberfläche. Im Linux-Mint-Menü kannst du nach `roccat` suchen. Der Menüeintrag verweist auf den Starter im installierten Projektordner unter `/usr/lib/roccat/roccat.desktop`.

Die udev-Regel vergibt dem Dienstkonto Zugriff auf die HID-Schnittstellen von Magma und Kone Pro. Die laufende udev-Instanz wendet sie bei der Paketinstallation auf verbundene Geräte an. Für die VM müssen die Geräte dorthin durchgereicht werden.

Bei Installation aus einer grafischen Sitzung erscheint zusätzlich ein ausführbarer Starter auf dem XDG-Schreibtisch. Das Paket legt den Starter für lokale grafische Sitzungen und für einen erkennbaren sudo-Benutzer an.

`sudo apt remove roccat` entfernt den Desktop-Starter, das Programmprotokoll des erfassten Benutzers, die Dienstaktivierung, den OpenRGB-Dienstzustand sowie das dafür angelegte Systemkonto und seine Gruppe. Persönliche Farbprofile bleiben erhalten. Bei Version 0.1.3 räumt dpkg seinen Paketeintrag bei der Entfernung mit auf. Für einen bereits verbliebenen Paketeintrag aus Version 0.1.2 kann einmalig `sudo apt purge roccat` ausgeführt werden.

## Beleuchtungszeit ab 0.1.4

Nach der Paketinstallation im Terminal der Cinnamon-Sitzung als Desktop-Benutzer
`roccat-lichtdienst` ausführen. Für einen Start aus dem Projektordner lautet der
entsprechende Befehl `./packaging/lighting-autostart`. Die Aktivierung übernimmt
`roccat-profil-start.service` und sichert eine bereits vorhandene Unit-Datei unter
`~/.config/systemd/user/roccat-profil-start.service.backup-*`. Die bisherige
Skriptdatei und die Profil-JSONs bleiben am bisherigen Pfad. Der Paketbau und die
Paketinstallation migrieren den Benutzerdienst nicht eigenständig.

Die neue Unit verwendet die letzte bestätigte aktive Zuordnung je Modell,
andernfalls die bestehenden Profile `pc-tastatur.json` und `pc-maus.json`.
Zeiteinstellungen und aktive Zuordnungen liegen neben dem Profilordner im
Benutzer-Konfigurationsverzeichnis `roccat`. Beim Aktualisieren existierender
Zeiteinstellungen wird vor dem ersten Überschreiben eine Sicherung angelegt.

Für eine Rückkehr zum alten Profilstart den neuen Dienst stoppen, die gesicherte
Unit zurückkopieren, `systemctl --user daemon-reload` ausführen und
`systemctl --user enable --now roccat-profil-start.service` aufrufen. Auf Systemen
ohne frühere Unit lässt sich der Dienst mit
`systemctl --user disable --now roccat-profil-start.service` deaktivieren.
