"""roccat GTK interface."""
import os
from pathlib import Path
import sys
from threading import Thread
from urllib.parse import urlsplit

from devices import BackendError, MODELS, inventory, sdk_operation
import profiles

ROOT = Path(__file__).resolve().parents[1]
shared_basis = ROOT.parent / ".basis"
local_basis = ROOT / ".basis"
sys.path.insert(0, str(local_basis if local_basis.is_dir() else shared_basis))
from basis import BasisFenster, Gdk, GLib, Gtk

TEXT = {
    "lighting": ("Beleuchtung", "Lighting"),
    "input": ("Tasten und Schaltflächen", "Keys and buttons"),  # Existing log entries.
    "profiles": ("Profile", "Profiles"),
    "diagnostics": ("Diagnose", "Diagnostics"),
    "check": ("OpenRGB prüfen", "Check OpenRGB"),
    "apply": ("Auf Gerät anwenden", "Apply to device"),
    "import": ("Profil importieren", "Import profile"),
    "export": ("Profil exportieren", "Export profile"),
    "save": ("Lokal speichern", "Save locally"),
    "load": ("Profil laden", "Load profile"),
    "duplicate": ("Duplizieren", "Duplicate"),
    "rename": ("Umbenennen", "Rename"),
    "ok": ("Bestätigen", "Confirm"),
    "cancel": ("Abbrechen", "Cancel"),
    "name": ("Profilname", "Profile name"),
    "mode": ("Modus", "Mode"),
    "area": ("LED-Bereich", "LED area"),
    "brightness": ("Helligkeit", "Brightness"),
    "speed": ("Tempo", "Speed"),
    "connected": ("USB-Gerät verbunden", "USB device connected"),
    "missing": ("USB-Gerät fehlt. In der VM ist USB-Durchreichen erforderlich.",
                "USB device absent. USB passthrough is required in the VM."),
    "unknown": ("unbekannt", "unknown"),
    "pending": ("OpenRGB wird abgefragt …", "Querying OpenRGB …"),
    "hid_missing": ("USB erkannt, aber noch keine HID-Schnittstelle sichtbar.",
                    "USB detected, but no HID interface is visible yet."),
    "hid_blocked": ("USB erkannt, aber mindestens eine HID-Schnittstelle ist für diesen Benutzer gesperrt.",
                    "USB detected, but at least one HID interface is inaccessible to this user."),
    "hid_ready": ("Die HID-Schnittstellen sind für diesen Benutzer zugänglich.",
                  "The HID interfaces are accessible to this user."),
    "unchecked": ("OpenRGB noch nicht geprüft.", "OpenRGB has not been checked."),
    "server_ready": ("OpenRGB SDK ist erreichbar.", "OpenRGB SDK is reachable."),
    "ready": ("OpenRGB hat den Controller eindeutig zugeordnet.", "OpenRGB controller identified."),
    "dependency": ("openrgb-python fehlt.", "openrgb-python is missing."),
    "start_openrgb": ("Bitte OpenRGB starten", "Start OpenRGB"),
    "start_openrgb_hint": (
        "Starte OpenRGB mit aktiviertem SDK-Server auf Port 6742 oder führe OpenRGB-starten.sh im Projektordner aus. Klicke anschließend auf „OpenRGB prüfen“.",
        "Start OpenRGB with its SDK server enabled on port 6742 or run OpenRGB-starten.sh in the project folder. Then select “Check OpenRGB”.",
    ),
    "disconnected": ("nicht verbunden", "not connected"),
    "offline": ("OpenRGB SDK lokal auf Port 6742 nicht erreichbar.", "Local OpenRGB SDK on port 6742 is unavailable."),
    "unmatched": ("Kein eindeutig passender SDK-Controller. OpenRGB-Erkennung, Gerätezugriff und konkurrierende Dienste prüfen.",
                  "No unique SDK controller match. Check OpenRGB detection, device access and competing services."),
    "removed": ("Das USB-Gerät wurde entfernt oder geändert.", "USB device was removed or changed."),
    "incompatible": ("Profil und gemeldete Gerätefähigkeiten passen nicht zusammen.",
                     "Profile and reported device capabilities do not match."),
    "failed": ("OpenRGB konnte den Vorgang nicht abschließen. Gerätezustand erneut prüfen.",
               "OpenRGB could not complete the operation. Check device state again."),
    "sent": ("An OpenRGB gesendet. Wirkung am Gerät kontrollieren.", "Sent to OpenRGB. Verify the effect on the device."),
    "all_colors": ("Farbe für alle Bereiche", "Color for all areas"),
    "persistence": ("Je nach Modus speichert das Gerät Änderungen dauerhaft.",
                    "Depending on the mode, device settings may persist."),
    "profile_ok": ("Profil verarbeitet. Laden und Speichern ändern das Gerät nicht.",
                   "Profile operation complete. Loading and saving do not change the device."),
    "profile_error": ("Profil ungültig, bereits vorhanden oder Datei nicht zugänglich.",
                      "Invalid profile, file already exists, or file cannot be accessed."),
    "keyd_export": ("keyd-Konfiguration exportieren", "Export keyd configuration"),
    "keyd_saved": ("Konfiguration exportiert. Sie wird erst durch keyd aktiv.",
                   "Configuration exported. It takes effect once loaded by keyd."),
    "keyd_error": ("Keine Zuordnung vorhanden oder Datei konnte nicht gespeichert werden.",
                   "No binding selected or file could not be saved."),
    "description": ("Erkennt ROCCAT Magma und Kone Pro, fragt OpenRGB ab und verwaltet lokale Beleuchtungsprofile.",
                    "Detects ROCCAT Magma and Kone Pro, queries OpenRGB and manages local lighting profiles."),
}


LOG_EVENTS = {
    "input.mapping_changed": ("Tastenbelegung bearbeitet.", "Key mapping edited."),
    "input.exported": ("{status}", "{status}"),
    "application.started": ("Anwendung gestartet.", "Application started."),
    "application.quit_requested": ("Beenden angefordert.", "Quit requested."),
    "application.window_closed": ("Anwendungsfenster geschlossen.", "Application window closed."),
    "theme.changed": ("Systemdesign geändert.", "System theme changed."),
    "language.changed": ("Sprache gewechselt.", "Language changed."),
    "log.opened": ("Protokoll geöffnet.", "Log file opened."),
    "settings.opened": ("Einstellungen geöffnet.", "Settings opened."),
    "help.opened": ("Hilfe geöffnet.", "Help opened."),
    "about.opened": ("Programminformation geöffnet.", "About opened."),
    "usb.connected": ("Gerät hinzugekommen: {model}.", "Device connected: {model}."),
    "usb.disconnected": ("Gerät entfernt: {model}.", "Device disconnected: {model}."),
    "usb.selected": ("Gerät ausgewählt: {model}.", "Device selected: {model}."),
    "usb.access_changed": ("HID-Zugriff: {status}", "HID access: {status}"),
    "ui.page_changed": ("Ansicht geöffnet: {action}.", "Page opened: {action}."),
    "lighting.mode_selected": ("Beleuchtungsmodus ausgewählt.", "Lighting mode selected."),
    "lighting.color_changed": ("Farbe geändert.", "Color changed."),
    "lighting.parameter_changed": ("Einstellung geändert: {action}.", "Setting changed: {action}."),
    "ui.requested": ("Aktion aufgerufen: {action}.", "Action requested: {action}."),
    "ui.cancelled": ("Aktion abgebrochen: {action}.", "Action cancelled: {action}."),
    "lighting.confirmed": ("Schreiben auf das Gerät bestätigt.", "Writing to the device confirmed."),
    "lighting.all_colors_changed": ("Farbe für alle Bereiche übernommen.", "Color copied to all areas."),
    "lighting.invalid": ("Anwenden fehlgeschlagen: Beleuchtungseinstellungen ungültig.",
                         "Apply failed: invalid lighting settings."),
    "openrgb.started": ("OpenRGB-Vorgang gestartet: {action}.", "OpenRGB operation started: {action}."),
    "openrgb.discarded": ("OpenRGB-Ergebnis verworfen: Geräteauswahl geändert.",
                          "OpenRGB result discarded: device selection changed."),
    "usb.inventory_changed": ("Erkannte ROCCAT-Geräte: {count}.", "ROCCAT devices detected: {count}."),
}
LOG_LEVELS_DE = {
    "DEBUG": "DEBUG", "INFO": "INFO", "WARNING": "WARNUNG",
    "ERROR": "FEHLER", "CRITICAL": "KRITISCH",
}


SDK_SUCCESS_STATES = {"server_ready", "ready", "sent"}
SDK_ERROR_STATES = {"offline", "dependency", "failed", "unmatched", "removed", "incompatible"}
SDK_RETRY_STATES = {"offline", "dependency", "failed", "unmatched"}


class Window(BasisFenster):
    logo_path = ROOT / "bilder" / "Roccat.svg"
    app_version = (ROOT / "VERSION").read_text().strip()
    reset_log_on_start = True

    def __init__(self, application):
        self.body = None
        super().__init__(application)
        self.resize(820, 630)
        self.device = None
        self.selection = ("3124", "")
        self.device_buttons = {}
        self.startup_check = True
        self.hid_state = None
        self.updating_modes = False
        self.devices = None
        self.busy = False
        self.closed = False
        self.status = "unchecked"
        self.capabilities = {}
        self.draft = None
        self.color_buttons = []
        self.all_color_control = None
        self.parameter_fields = {}
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=18)
        self.content.pack_start(self.body, True, True, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_overlay_scrolling(False)
        self.body.pack_start(scroll, True, True, 0)
        lighting = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=14)
        scroll.add(lighting)
        self.device_choices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lighting.pack_start(self.device_choices, False, False, 0)
        self.connection = Gtk.Label(xalign=0, wrap=True, halign=Gtk.Align.START)
        lighting.pack_start(self.connection, False, False, 0)
        self.hid_status = Gtk.Label(xalign=0, wrap=True)
        lighting.pack_start(self.hid_status, False, False, 0)
        self.buttons = {}
        self.button(lighting, "check", self.run_sdk)
        self.buttons["check"].set_no_show_all(True)
        self.mode = Gtk.ComboBoxText()
        self.mode.connect("changed", self.mode_changed)
        self.mode_label = Gtk.Label(xalign=0)
        lighting.pack_start(self.mode_label, False, False, 0)
        lighting.pack_start(self.mode, False, False, 0)
        self.controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        lighting.pack_start(self.controls, False, False, 0)
        self.button(lighting, "apply", self.apply_current)
        self.persistence = Gtk.Label(xalign=0, wrap=True)
        lighting.pack_start(self.persistence, False, False, 0)
        self.lighting_status = Gtk.Label(xalign=0, wrap=True, halign=Gtk.Align.START)
        status_style = Gtk.CssProvider()
        status_style.load_from_data(b"""
            label.status-success, label.status-error {
                border-radius: 6px;
                padding: 5px 9px;
                font-weight: bold;
            }
            label.status-success {
                color: #15552b;
                background-color: #e2f5e6;
            }
            label.status-error {
                color: #8e2525;
                background-color: #fce8e7;
            }
        """)
        for label in (self.connection, self.lighting_status):
            label.get_style_context().add_provider(status_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        lighting.pack_start(self.lighting_status, False, False, 0)
        menu_bar = self.file_item.get_parent()
        self.profiles_item = Gtk.MenuItem()
        profiles_menu = Gtk.Menu()
        self.profiles_item.set_submenu(profiles_menu)
        menu_bar.insert(self.profiles_item, 1)
        self.profile_actions = {
            action: self.add_item(profiles_menu, lambda action=action: self.local_profile(action))
            for action in ("load", "save", "duplicate", "rename")
        }
        profiles_menu.append(Gtk.SeparatorMenuItem())
        for action in ("import", "export"):
            self.profile_actions[action] = self.add_item(
                profiles_menu, lambda action=action: self.transfer(action)
            )
        self.profile_status = Gtk.Label(xalign=0, wrap=True, no_show_all=True)
        self.body.pack_start(self.profile_status, False, False, 0)
        self.profile_message = None
        self.set_language(self.language)
        self.scan()
        self.timer = GLib.timeout_add_seconds(2, self.scan)
        self.connect("destroy", self.shutdown)
        self.show_all()
        self.run_sdk()

    def t(self, key):
        return TEXT[key][self.language == "en"]

    def button(self, parent, key, callback):
        widget = Gtk.Button(halign=Gtk.Align.START)
        widget.connect("clicked", lambda _: callback())
        parent.pack_start(widget, False, False, 0)
        self.buttons[key] = widget

    def set_language(self, language):
        super().set_language(language)
        self.set_title(f"roccat {self.app_version}")
        if self.about_window is not None:
            self.about_name.set_markup("<big><b>roccat</b></big>")
            self.about_label.set_text(self.t("description"))
        if self.body is None:
            return
        self.update_device_labels()
        for key, widget in self.buttons.items():
            widget.set_label(self.t(key))
        self.profiles_item.set_label(self.t("profiles"))
        for action, item in self.profile_actions.items():
            item.set_label(self.t(action))
        self.mode_label.set_text(self.t("mode"))
        self.persistence.set_text(self.t("persistence"))
        if self.all_color_control:
            label, button = self.all_color_control
            label.set_text(self.t("all_colors"))
            button.set_title(self.t("all_colors"))
        for index, (label, _) in enumerate(self.color_buttons, 1):
            label.set_text(f"{self.t('area')} {index}")
        for key, (label, _) in self.parameter_fields.items():
            label.set_text(self.t(key))
        self.update_status()

    def format_log_line(self, line):
        header = line.split(maxsplit=4)
        if len(header) < 4:
            return line
        date, time, level, event = header[:4]
        values = dict(token.split("=", 1) for token in header[-1].split() if "=" in token) if len(header) == 5 else {}
        messages = LOG_EVENTS.get(event)
        if messages:
            unknown = self.t("unknown")
            action = values.get("action")
            status = values.get("status")
            model = MODELS.get(values.get("model"))
            message = messages[self.language == "en"].format(
                count=values.get("count", unknown),
                action=self.t(action) if action in TEXT else unknown,
                status=self.t(status) if status in TEXT else unknown,
                model=model[0] if model else unknown,
            )
        elif event == "openrgb.result" and values.get("status") in TEXT:
            message = self.t(values["status"])
        elif event.startswith("profile.") and event[8:] in {"load", "save", "duplicate", "rename", "import", "export"}:
            result = "profile_ok" if values.get("success") == "True" else "profile_error"
            message = f"{self.t(event[8:])} · {self.t(result)}"
        else:
            return line
        if self.language == "de":
            level = LOG_LEVELS_DE.get(level, level)
        return f"{date} {time} {level} {message}\n"

    def show_about(self):
        super().show_about()
        self.set_language(self.language)

    def load_help(self):
        anchor = urlsplit(self.help_view.get_uri() or "").fragment
        path = ROOT / "hilfe" / f"hilfe-{self.language}.html"
        self.help_view.load_uri(path.as_uri() + (f"#{anchor}" if anchor else ""))

    def scan(self):
        found = inventory()
        if found == self.devices:
            self.update_hid_status()
            return True
        if self.devices is not None:
            for device in self.devices:
                if device not in found:
                    self.log_event("usb.disconnected model=%s", device.product)
            for device in found:
                if device not in self.devices:
                    self.log_event("usb.connected model=%s", device.product)
        self.devices = found
        for button in self.device_buttons.values():
            button.destroy()
        self.device_buttons.clear()
        connected = {(device.product, device.port): device for device in found}
        model, _ = self.selection
        if self.selection not in connected:
            same_model = next((key for key in connected if key[0] == model), None)
            self.selection = same_model or next(iter(connected), (model, ""))
        for product in MODELS:
            choices = [key for key in connected if key[0] == product] or [(product, "")]
            for key in choices:
                button = Gtk.CheckButton()
                button.set_active(key == self.selection)
                button.connect("toggled", self.select_device, key)
                self.device_choices.pack_start(button, False, False, 0)
                self.device_buttons[key] = button
        self.update_device_labels()
        self.device_choices.show_all()
        self.update_selected_device()
        self.log_event("usb.inventory_changed count=%d", len(found))
        return True

    def update_device_labels(self):
        for (model, port), button in self.device_buttons.items():
            suffix = f"USB {port}" if port else self.t("disconnected")
            button.set_label(f"{MODELS[model][0]} · {suffix}")

    def select_device(self, button, key):
        if not button.get_active():
            if key == self.selection:
                button.set_active(True)
            return
        if key == self.selection:
            return
        previous = self.selection
        self.selection = key
        self.device_buttons[previous].set_active(False)
        self.log_event("usb.selected model=%s", key[0])
        self.update_selected_device()

    def update_selected_device(self):
        device = next((item for item in self.devices if (item.product, item.port) == self.selection), None)
        if device != self.device:
            self.device = device
            self.status = "unchecked"
            self.set_modes({}, "")
            if not self.startup_check:
                self.run_sdk()
        self.update_status()

    def set_status_label(self, label, status, *, success=False, error=False):
        label.set_text(self.t(status))
        style = label.get_style_context()
        for css_class, active in (("status-success", success), ("status-error", error)):
            if active:
                style.add_class(css_class)
            else:
                style.remove_class(css_class)

    def update_status(self):
        connected = self.device is not None
        self.set_status_label(self.connection, "connected" if connected else "missing",
                              success=connected, error=not connected)
        self.update_hid_status()
        status = "pending" if self.busy else self.status
        self.set_status_label(self.lighting_status, status, success=status in SDK_SUCCESS_STATES,
                              error=status in SDK_ERROR_STATES)
        retry = self.buttons["check"]
        retry.set_visible(self.status in SDK_RETRY_STATES)
        retry.set_sensitive(not self.busy)
        self.buttons["apply"].set_sensitive(bool(self.device and self.mode.get_active_id()) and not self.busy)
        self.profile_status.set_text(self.t(self.profile_message) if self.profile_message else "")
        self.profile_status.set_visible(self.profile_message is not None)

    def update_hid_status(self):
        if self.device is None:
            self.hid_state = None
            self.hid_status.set_text("")
            return
        if not self.device.hid:
            status = "hid_missing"
        elif not all(os.access(path, os.R_OK | os.W_OK) for path in self.device.hid):
            status = "hid_blocked"
        else:
            status = "hid_ready"
        if status != self.hid_state:
            self.hid_state = status
            self.log_event("usb.access_changed status=%s", status)
        self.hid_status.set_text(self.t(status))

    def set_modes(self, capabilities, active):
        self.updating_modes = True
        self.capabilities = capabilities
        self.mode.remove_all()
        for name in capabilities:
            self.mode.append(name, name)
        if capabilities and not self.mode.set_active_id(active):
            self.mode.set_active(0)
        self.mode_changed()
        self.updating_modes = False

    def add_control(self, label_text, widget):
        row = Gtk.Box(spacing=10)
        label = Gtk.Label(label=label_text, xalign=0)
        row.pack_start(label, True, True, 0)
        row.pack_end(widget, False, False, 0)
        self.controls.pack_start(row, False, False, 0)
        return label, widget

    def mode_changed(self, *_):
        for child in self.controls.get_children():
            child.destroy()
        self.all_color_control = None
        self.color_buttons.clear()
        self.parameter_fields.clear()
        mode = self.mode.get_active_id()
        if mode in self.capabilities:
            if not self.updating_modes:
                self.log_event("lighting.mode_selected")
            entries, limits = self.capabilities[mode]
            if len(entries) > 1:
                color = Gdk.RGBA()
                color.parse(entries[0])
                widget = Gtk.ColorButton(rgba=color, title=self.t("all_colors"))
                widget.connect("color-set", self.set_all_colors)
                self.all_color_control = self.add_control(self.t("all_colors"), widget)
            for index, entry in enumerate(entries, 1):
                color = Gdk.RGBA()
                color.parse(entry)
                widget = Gtk.ColorButton(rgba=color)
                widget.connect("color-set", lambda _: self.log_event("lighting.color_changed"))
                self.color_buttons.append(self.add_control(f"{self.t('area')} {index}", widget))
            for key, (low, high, value) in limits.items():
                widget = Gtk.SpinButton.new_with_range(low, high, 1)
                widget.set_value(value)
                widget.connect("value-changed", self.parameter_changed, key)
                self.parameter_fields[key] = self.add_control(self.t(key), widget)
        self.controls.show_all()
        self.update_status()

    def set_all_colors(self, chooser):
        rgba = chooser.get_rgba()
        for _, button in self.color_buttons:
            button.set_rgba(rgba)
        self.log_event("lighting.all_colors_changed")

    def parameter_changed(self, _, key):
        if not self.updating_modes:
            self.log_event("lighting.parameter_changed action=%s", key)

    def current_profile(self, name):
        mode = self.mode.get_active_id()
        if not mode:
            if self.draft and self.draft["product"] == self.model():
                return dict(self.draft, name=name)
            raise ValueError("mode")
        colors = []
        for _, button in self.color_buttons:
            rgba = button.get_rgba()
            colors.append("#" + "".join(f"{round(value * 255):02x}" for value in (rgba.red, rgba.green, rgba.blue)))
        return profiles.validate({
            "schema": 1, "vendor": "1e7d", "product": self.model(),
            "name": name, "backend": "OpenRGB", "mode": mode, "colors": colors,
            "parameters": {key: int(field.get_value()) for key, (_, field) in self.parameter_fields.items()},
        })

    def model(self):
        return self.selection[0]

    def load_profile(self, profile):
        if profile["product"] != self.model():
            raise ValueError("device")
        self.draft = profile
        self.updating_modes = True
        try:
            self.stage_profile()
        finally:
            self.updating_modes = False

    def stage_profile(self):
        profile = self.draft
        if not profile or profile["product"] != self.model():
            return
        if not self.capabilities:
            return
        mode = profile["mode"]
        if mode not in self.capabilities:
            raise ValueError("mode")
        entries, limits = self.capabilities[mode]
        params = profile["parameters"]
        if len(entries) != len(profile["colors"]) or set(limits) != set(params):
            raise ValueError("capabilities")
        if any(not limits[key][0] <= value <= limits[key][1] for key, value in params.items()):
            raise ValueError("range")
        self.mode.set_active_id(mode)
        for (_, button), value in zip(self.color_buttons, profile["colors"]):
            color = Gdk.RGBA()
            color.parse(value)
            button.set_rgba(color)
        for key, value in params.items():
            self.parameter_fields[key][1].set_value(value)

    def ask_name(self, key, initial=""):
        dialog = Gtk.Dialog(title=self.t(key), transient_for=self, modal=True)
        dialog.add_button(self.t("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self.t("ok"), Gtk.ResponseType.OK)
        entry = Gtk.Entry(text=initial, placeholder_text=self.t("name"), activates_default=True, max_length=60, margin=12)
        dialog.get_content_area().add(entry)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        name = entry.get_text().strip() if dialog.run() == Gtk.ResponseType.OK else None
        dialog.destroy()
        if name is None:
            self.log_event("ui.cancelled action=%s", key)
        elif not profiles.NAME.fullmatch(name):
            raise ValueError("name")
        return name

    def choose_file(self, key, *, save=False, local=False):
        action = Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN
        dialog = Gtk.FileChooserDialog(title=self.t(key), transient_for=self, action=action)
        dialog.add_button(self.t("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self.t("ok"), Gtk.ResponseType.OK)
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern("*.json")
        file_filter.set_name("JSON")
        dialog.add_filter(file_filter)
        if local:
            profiles.DIRECTORY.mkdir(parents=True, mode=0o700, exist_ok=True)
            dialog.set_current_folder(str(profiles.DIRECTORY))
        if save:
            dialog.set_current_name("roccat.json")
            dialog.set_do_overwrite_confirmation(True)
        path = dialog.get_filename() if dialog.run() == Gtk.ResponseType.OK else None
        dialog.destroy()
        if path is None:
            self.log_event("ui.cancelled action=%s", key)
        if path and local and Path(path).parent.resolve() != profiles.DIRECTORY.resolve():
            raise ValueError("directory")
        return Path(path) if path else None

    def local_profile(self, action):
        self.log_event("ui.requested action=%s", action)
        try:
            if action == "save":
                initial = self.draft["name"] if self.draft else ""
                name = self.ask_name(action, initial)
                if name is None:
                    return
                profiles.save(profiles.DIRECTORY / f"{name}.json", self.current_profile(name))
            else:
                path = self.choose_file(action, local=True)
                if path is None:
                    return
                profile = profiles.load(path)
                if action == "load":
                    self.load_profile(profile)
                else:
                    name = self.ask_name(action, profile["name"])
                    if name is None:
                        return
                    target = profiles.DIRECTORY / f"{name}.json"
                    profiles.save(target, dict(profile, name=name))
                    if action == "rename":
                        path.unlink()
        except (ValueError, OSError, UnicodeError, RecursionError):
            self.profile_result(action, False)
        else:
            self.profile_result(action, True)

    def transfer(self, action):
        self.log_event("ui.requested action=%s", action)
        try:
            exporting = action == "export"
            path = self.choose_file(action, save=exporting)
            if path is None:
                return
            if exporting:
                name = self.draft["name"] if self.draft else "roccat"
                profiles.save(path, self.current_profile(name), replace=True)
            else:
                self.load_profile(profiles.load(path))
        except (ValueError, OSError, UnicodeError, RecursionError):
            self.profile_result(action, False)
        else:
            self.profile_result(action, True)

    def profile_result(self, action, success):
        self.profile_message = "profile_ok" if success else "profile_error"
        self.update_status()
        self.log_event("profile.%s success=%s", action, success)

    def apply_current(self):
        self.log_event("ui.requested action=apply")
        try:
            settings = self.current_profile("roccat")
        except ValueError:
            self.log_event("lighting.invalid")
            return
        self.run_sdk(settings)

    def run_sdk(self, settings=None):
        device = self.device
        if self.busy or (device is None and settings is not None):
            return
        self.busy = True
        self.log_event("openrgb.started action=%s", "apply" if settings else "check")
        self.update_status()

        def run():
            result, status = None, "server_ready" if device is None else "ready"
            if settings is not None:
                status = "sent"
            try:
                result = sdk_operation(device, settings)
            except BackendError as error:
                status = str(error)
            except Exception:
                status = "failed"
            GLib.idle_add(self.sdk_result, device, result, status)

        Thread(target=run, daemon=True).start()

    def sdk_result(self, device, result, status):
        if self.closed:
            return
        self.busy = False
        first_check = self.startup_check
        self.startup_check = False
        self.log_event("openrgb.result status=%s", status)
        if device == self.device:
            self.status = status
            if result and status != "sent":
                self.set_modes(*result)
                self.updating_modes = True
                try:
                    self.stage_profile()
                except ValueError:
                    self.profile_result("load", False)
                finally:
                    self.updating_modes = False
            elif not result:
                self.set_modes({}, "")
        else:
            self.log_event("openrgb.discarded")
            self.run_sdk()
        self.update_status()
        if first_check and status in {"offline", "dependency"}:
            self.prompt_openrgb(status)

    def prompt_openrgb(self, status):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True, destroy_with_parent=True,
            message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK,
            text=self.t("start_openrgb") if status == "offline" else self.t("dependency"),
            secondary_text=self.t("start_openrgb_hint") if status == "offline" else None,
        )
        dialog.connect("response", lambda widget, _: widget.destroy())
        dialog.show()

    def shutdown(self, _):
        self.closed = True
        GLib.source_remove(self.timer)


class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="local.labor.roccat")
        icon = Window.logo_path
        if not icon.is_file():
            icon = ROOT / ".basisbilder" / "start.png"
        if not icon.is_file():
            icon = ROOT.parent / ".basisbilder" / "start.png"
        if icon.is_file():
            Gtk.Window.set_default_icon_from_file(str(icon))

    def do_activate(self):
        (self.get_active_window() or Window(self)).present()


if __name__ == "__main__":
    if os.geteuid() == 0:
        sys.exit("roccat als normaler Benutzer starten. / Run roccat as a regular user.")
    sys.exit(Application().run(sys.argv))
