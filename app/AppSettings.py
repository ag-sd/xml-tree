import pickle
from collections import deque
from enum import unique, Enum

from PyQt5.QtCore import QObject, pyqtSignal, QSettings
from PyQt5.QtGui import QFont

import app


class Settings(QObject):
    """
    A class that can read and write application settings. The class can also fire events
    when a setting changes.
    App specific settings are stored as a dictionary that is saved as a byte stream
    """
    settings_change_event = pyqtSignal(object, object)

    def __init__(self, app_name, default_settings):
        super().__init__()
        self._app_settings = QSettings("github.com/ag-sd", app_name)
        self._config = self._app_settings.value("app_settings")
        if self._config is None:
            self._config = default_settings

    def apply_setting(self, key, value):
        """
        Save an internal setting and fire an event
        :param key: the setting key
        :param value: the value to set
        :return:
        """
        app.logger.info(f"{key} -> {value}")
        self._config[key] = value
        self._app_settings.setValue("app_settings", self._config)
        self.settings_change_event.emit(key, value)

    def get_setting(self, key, default=None):
        if self._config.__contains__(key):
            return self._config[key]
        return default


@unique
class SettingsKeys(Enum):
    recent_documents = "recent_documents"
    max_recent = "max_recent"
    toggle_attributes = "show_attributes"
    font = "font"
    syntax_highlighting = "syntax_highlighting."


__DEFAULT_COLOR_THEME = {
    "attribute": "#778899",
    "comment": "#228b22",
    "key": "#800080",
    "node": "#0000ff",
    "value": "#000000",
    "highlight": "#ffff00"
}

settings = Settings(
    app.__APP_NAME__,
    {}
)


def show_attributes():
    return settings.get_setting(SettingsKeys.toggle_attributes, True)


def set_show_attributes(value):
    settings.apply_setting(SettingsKeys.toggle_attributes, value)


def get_recent_files():
    return settings.get_setting(SettingsKeys.recent_documents)


def font():
    font_string = settings.get_setting(SettingsKeys.font, None)
    if font_string:
        _font = QFont()
        if _font.fromString(font_string):
            return _font
    return None


def set_font(_font):
    settings.apply_setting(SettingsKeys.font, _font.toString())


def color_theme():
    pickled = settings.get_setting(SettingsKeys.syntax_highlighting)
    if pickled:
        return pickle.loads(pickled)
    else:
        return __DEFAULT_COLOR_THEME


def set_color_theme(theme):
    settings.apply_setting(SettingsKeys.syntax_highlighting, pickle.dumps(theme))


def add_to_recent(file):
    recent_files = settings.get_setting(SettingsKeys.recent_documents, deque([]))
    max_recent_files = settings.get_setting(SettingsKeys.max_recent, 10)
    # Move the current file to the bottom
    remove_from_recent(file)
    recent_files.append(file)
    while len(recent_files) > max_recent_files:
        recent_files.popleft()
    settings.apply_setting(SettingsKeys.recent_documents, recent_files)


def remove_from_recent(file):
    recent_files = settings.get_setting(SettingsKeys.recent_documents, deque([]))
    try:
        recent_files.remove(file)
    except ValueError:
        pass

