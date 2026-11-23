"""Gemeinsames GTK-3-Grundfenster für Python-Projekte."""
from collections import deque
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from urllib.parse import urlsplit

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_foreign("cairo")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, WebKit2

TEXT = {
    "de": ("Python-Basis", "Datei", "Einstellungen", "Beenden", "Hilfe",
           "Über", "Sprache", "Stellt ein GTK-Grundfenster, einen sofortigen Sprachwechsel und eine integrierte HTML-Hilfe für neue Python-Anwendungen bereit."),
    "en": ("Python base", "File", "Settings", "Quit", "Help",
           "About", "Language", "Provides a GTK window, instant language switching and built-in HTML help for new Python applications."),
}


ABOUT_TEXT = {
    "de": ("Info", "Mitwirkende", "Keine Mitwirkenden eingetragen."),
    "en": ("Info", "Credits", "No contributors listed."),
}


CREDITS_TEXT = {
    "de": ("Entwicklung, Tests und Dokumentation",
           "Meine Projekte und Erfahrungen rund um Linux Mint und Python.",
           "Dogtruck besuchen", "GitHub-Profil öffnen"),
    "en": ("Development, testing and documentation",
           "My projects and experiences with Linux Mint and Python.",
           "Visit Dogtruck", "Open GitHub profile"),
}


class BannerBild(Gtk.DrawingArea):
    def __init__(self, path):
        super().__init__()
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_get_preferred_height_for_width(self, width):
        height = round(width * self.pixbuf.get_height() / self.pixbuf.get_width())
        return height, height

    def do_draw(self, context):
        scale = min(self.get_allocated_width() / self.pixbuf.get_width(),
                    self.get_allocated_height() / self.pixbuf.get_height())
        context.save()
        context.translate((self.get_allocated_width() - self.pixbuf.get_width() * scale) / 2, 0)
        context.scale(scale, scale)
        Gdk.cairo_set_source_pixbuf(context, self.pixbuf, 0, 0)
        context.paint()
        context.restore()
        return False


class BasisFenster(Gtk.ApplicationWindow):
    app_version = "0.1.0"
    logo_path = None
    contributors = ("Josef Lehner",)
    license_link = None
    hidden_log_events = frozenset()
    reset_log_on_start = False

    def __init__(self, application):
        super().__init__(application=application, default_width=720, default_height=460)
        self.language = next(
            (code[:2] for code in GLib.get_language_names() if code[:2] in TEXT), "de"
        )
        self.settings_window = self.help_window = self.about_window = self.log_window = None
        self.log_path = Path(GLib.get_user_state_dir()) / application.get_application_id() / "programm.log"
        self.logger = logging.Logger(application.get_application_id(), logging.INFO)
        self.log_handler = None
        try:
            self.log_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if self.reset_log_on_start:
                self.log_path.write_text("", encoding="utf-8")
                for number in (1, 2):
                    self.log_path.with_name(f"{self.log_path.name}.{number}").unlink(missing_ok=True)
            self.log_handler = RotatingFileHandler(
                self.log_path, maxBytes=256 * 1024, backupCount=2, encoding="utf-8"
            )
            self.log_handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S"
            ))
            self.logger.addHandler(self.log_handler)
        except OSError:
            self.logger.addHandler(logging.NullHandler())
        self.log_event("application.started")
        self.connect("destroy", self.close_log)
        self.theme_settings = self.get_settings()
        self.theme_signals = [
            self.theme_settings.connect(f"notify::{name}", self.theme_changed)
            for name in ("gtk-theme-name", "gtk-application-prefer-dark-theme")
        ]
        self.accels = Gtk.AccelGroup()
        self.add_accel_group(self.accels)

        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(layout)
        menu = Gtk.MenuBar()
        layout.pack_start(menu, False, False, 0)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        workspace = Gtk.Overlay()
        watermark_path = Path(__file__).resolve().parents[1] / ".basisbilder" / "wasserzeichen.png"
        watermark = Gtk.Image(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        watermark.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_scale(str(watermark_path), 256, 256, True)
        )
        watermark.set_opacity(0.12)
        workspace.add(watermark)
        workspace.add_overlay(self.content)
        layout.pack_start(workspace, True, True, 0)

        self.file_item, file_menu = self.add_menu(menu)
        self.settings_item = self.add_item(file_menu, self.show_settings)
        self.quit_item = self.add_item(file_menu, self.quit_application, Gdk.KEY_q)
        self.help_item, help_menu = self.add_menu(menu)
        self.open_help_item = self.add_item(help_menu, self.show_help, Gdk.KEY_F1)
        self.about_item = self.add_item(help_menu, self.show_about)
        self.log_item = self.add_item(help_menu, self.show_log)
        self.set_language(self.language)
        self.show_all()

    def log_event(self, message, *args, level=logging.INFO):
        self.logger.log(level, message, *args)

    def theme_changed(self, _, property_spec):
        self.log_event("theme.changed property=%s", property_spec.name)

    def quit_application(self):
        self.log_event("application.quit_requested")
        application = self.get_application()
        self.destroy()
        application.quit()

    def close_log(self, _):
        for signal in self.theme_signals:
            self.theme_settings.disconnect(signal)
        self.log_event("application.window_closed")
        if self.log_handler is not None:
            self.logger.removeHandler(self.log_handler)
            self.log_handler.close()

    def show_log(self):
        self.log_event("log.opened")
        if self.log_window is None:
            window = self.child_window("log_window", self.log_item.get_label(), width=750, height=440)
            scroll = Gtk.ScrolledWindow()
            self.log_view = Gtk.TextView(editable=False, cursor_visible=False, monospace=True,
                                         wrap_mode=Gtk.WrapMode.WORD_CHAR, left_margin=10,
                                         right_margin=10, top_margin=8, bottom_margin=8)
            scroll.add(self.log_view)
            window.add(scroll)
            self.log_contents = None
            self.refresh_log()
            timer = GLib.timeout_add_seconds(1, self.refresh_log)
            window.connect("destroy", lambda _: GLib.source_remove(timer))
            window.show_all()
        self.log_window.present()

    @staticmethod
    def log_event_name(line):
        parts = line.split(maxsplit=4)
        return parts[3] if len(parts) >= 4 else ""

    def format_log_line(self, line):
        return line

    def refresh_log(self, force=False):
        try:
            with self.log_path.open(encoding="utf-8", errors="replace") as stream:
                lines = (line for line in stream
                         if self.log_event_name(line) not in self.hidden_log_events)
                text = "".join(self.format_log_line(line) for line in deque(lines, maxlen=250))
        except OSError:
            text = ("Die Protokolldatei ist nicht verfügbar." if self.language == "de"
                    else "The log file is unavailable.")
        if force or text != self.log_contents:
            self.log_contents = text
            buffer = self.log_view.get_buffer()
            buffer.set_text(text)
            mark = buffer.get_insert()
            buffer.move_mark(mark, buffer.get_end_iter())
            self.log_view.scroll_to_mark(mark, 0, False, 0, 0)
        return GLib.SOURCE_CONTINUE

    def add_menu(self, menubar):
        item = Gtk.MenuItem()
        submenu = Gtk.Menu()
        item.set_submenu(submenu)
        menubar.append(item)
        return item, submenu

    def add_item(self, menu, callback, key=None):
        item = Gtk.MenuItem()
        item.connect("activate", lambda _: callback())
        menu.append(item)
        if key is not None:
            item.add_accelerator("activate", self.accels, key, 0, Gtk.AccelFlags.VISIBLE)
        return item

    def set_language(self, language):
        if self.language != language:
            self.log_event("language.changed language=%s", language)
        self.language = language
        self.log_item.set_label("Protokoll" if language == "de" else "Log file")
        if self.log_window is not None:
            self.log_window.set_title(self.log_item.get_label())
        if self.log_window is not None:
            self.refresh_log(force=True)
        title, file, settings, quit_, help_, about, language_label, description = TEXT[language]
        self.set_title(title)
        for item, label in (
            (self.file_item, file), (self.settings_item, settings),
            (self.quit_item, quit_), (self.help_item, help_),
            (self.open_help_item, help_), (self.about_item, about),
        ):
            item.set_label(label)
        if self.settings_window is not None:
            self.settings_window.set_title(settings)
            self.language_label.set_text(language_label)
        if self.about_window is not None:
            self.about_window.set_title(about)
            self.about_name.set_markup(f"<big><b>{GLib.markup_escape_text(title)}</b></big>")
            self.about_label.set_text(description)
            info, credits, empty = ABOUT_TEXT[language]
            self.about_stack.child_set_property(self.about_info, "title", info)
            self.about_stack.child_set_property(self.about_credits_page, "title", credits)
            self.about_credits.set_text("\n".join(self.contributors) or empty)
            link_label = "Dogtruck-Webseite öffnen" if language == "de" else "Open the Dogtruck website"
            self.website_button.set_tooltip_text(link_label)
            self.website_button.get_accessible().set_name(link_label)
            role, summary, website, github = CREDITS_TEXT[language]
            self.credits_role.set_text(role)
            self.dogtruck_summary.set_text(summary)
            self.dogtruck_link.set_label(website)
            self.github_link.set_label(github)
        if self.help_window is not None:
            self.help_window.set_title(help_)
            self.load_help()

    def child_window(self, attribute, title, *, width=340, height=-1):
        window = Gtk.Window(title=title, transient_for=self, destroy_with_parent=True,
                            default_width=width, default_height=height)
        setattr(self, attribute, window)
        window.connect("destroy", lambda _: setattr(self, attribute, None))
        return window

    def show_settings(self):
        self.log_event("settings.opened")
        if self.settings_window is None:
            window = self.child_window("settings_window", TEXT[self.language][2])
            row = Gtk.Box(spacing=12, margin=18)
            window.add(row)
            self.language_label = Gtk.Label(label=TEXT[self.language][6])
            choice = Gtk.ComboBoxText()
            choice.append("de", "Deutsch")
            choice.append("en", "English")
            choice.set_active_id(self.language)
            self.language_label.set_mnemonic_widget(choice)
            choice.connect("changed", lambda combo: self.set_language(combo.get_active_id()))
            row.pack_start(self.language_label, False, False, 0)
            row.pack_end(choice, True, True, 0)
            window.show_all()
        self.settings_window.present()

    def load_help(self):
        anchor = urlsplit(self.help_view.get_uri() or "").fragment
        path = Path(__file__).with_name(f"hilfe-{self.language}.html").resolve()
        self.help_view.load_uri(path.as_uri() + (f"#{anchor}" if anchor else ""))

    def show_help(self):
        self.log_event("help.opened")
        if self.help_window is None:
            window = self.child_window("help_window", TEXT[self.language][4],
                                       width=680, height=530)
            self.help_view = WebKit2.WebView()
            window.add(self.help_view)
            self.load_help()
            window.show_all()
        self.help_window.present()

    def show_about(self):
        self.log_event("about.opened")
        if self.about_window is None:
            window = self.child_window("about_window", TEXT[self.language][5],
                                       width=540, height=380)
            self.about_stack = Gtk.Stack()
            switcher = Gtk.StackSwitcher(stack=self.about_stack)
            header = Gtk.HeaderBar(show_close_button=True, decoration_layout=":close")
            header.set_custom_title(switcher)
            window.set_titlebar(header)
            window.add(self.about_stack)

            self.about_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                      spacing=12, margin=24, valign=Gtk.Align.CENTER)
            if self.logo_path:
                logo = Gtk.Image.new_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(str(self.logo_path), 144, 144, True)
                )
            else:
                logo = Gtk.Image.new_from_icon_name("applications-development", Gtk.IconSize.DIALOG)
                logo.set_pixel_size(112)
            self.about_name = Gtk.Label()
            self.about_label = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
            for widget in (logo, self.about_name, Gtk.Label(label=self.app_version), self.about_label):
                self.about_info.pack_start(widget, False, False, 0)
            if self.license_link:
                name, url = self.license_link
                self.about_info.pack_start(Gtk.LinkButton(uri=url, label=name), False, False, 0)
            self.about_credits_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            self.about_credits = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
            website_image = Path(__file__).resolve().parents[1] / ".basisbilder" / "webseite.png"
            self.website_button = Gtk.LinkButton(uri="https://dogtruck.eu", label="")
            self.website_button.remove(self.website_button.get_child())
            self.website_button.add(BannerBild(website_image))
            self.website_button.set_relief(Gtk.ReliefStyle.NONE)
            self.about_credits_page.pack_start(self.website_button, False, False, 0)
            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                              margin_start=20, margin_end=20, margin_bottom=18)
            details.pack_start(self.about_credits, False, False, 0)
            self.credits_role = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
            details.pack_start(self.credits_role, False, False, 0)
            dogtruck = Gtk.Label()
            dogtruck.set_markup("<b>Dogtruck</b>")
            dogtruck.set_margin_top(10)
            details.pack_start(dogtruck, False, False, 0)
            self.dogtruck_summary = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
            details.pack_start(self.dogtruck_summary, False, False, 0)
            links = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
            self.dogtruck_link = Gtk.LinkButton(uri="https://dogtruck.eu", label="")
            self.github_link = Gtk.LinkButton(uri="https://github.com/Lehner-007", label="")
            links.pack_start(self.dogtruck_link, False, False, 0)
            links.pack_start(self.github_link, False, False, 0)
            details.pack_start(links, False, False, 0)
            self.about_credits_page.pack_start(details, False, False, 0)
            self.about_stack.add_titled(self.about_info, "info", "Info")
            self.about_stack.add_titled(self.about_credits_page, "credits", "")
            self.set_language(self.language)
            self.about_stack.set_visible_child(self.about_info)
            window.show_all()
        self.about_window.present()


class BasisAnwendung(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="local.labor.PythonBasis")

    def do_activate(self):
        window = self.get_active_window() or BasisFenster(self)
        window.present()


if __name__ == "__main__":
    sys.exit(BasisAnwendung().run(sys.argv))
