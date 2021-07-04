from enum import Enum
from functools import partial

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QColor
from PyQt5.QtWidgets import QMenuBar, QAction, QMenu

import app
from app import AppSettings


class MenuAction(Enum):
    OPEN = "Open ..."
    RECENT = "Recent Documents"
    EXIT = "Exit"
    SEARCH = "Search Window"
    EXPAND = "Expand"
    COLLAPSE = "Collapse"
    RELOAD = "Reload file"
    ATTRIBUTES = "Show Attributes"
    COLOR = "Color Theme"
    FONT = "Change Font ..."
    HIDE = "Hide from view"
    TOP = "Go to top"
    BOTTOM = "Go to bottom"
    ABOUT = "About"


class XMLTreeViewContextMenu(QMenu):
    menu_event = pyqtSignal(MenuAction, object)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.addAction(_create_action(self, MenuAction.EXPAND.value, self.raise_event,
                                      icon=QIcon.fromTheme("list-add"), data=MenuAction.EXPAND))
        self.addAction(_create_action(self, MenuAction.COLLAPSE.value, self.raise_event,
                                      icon=QIcon.fromTheme("list-remove"), data=MenuAction.COLLAPSE))
        self.addAction(_create_action(self, MenuAction.HIDE.value, self.raise_event,
                                      icon=QIcon.fromTheme("edit-delete"), data=MenuAction.HIDE))
        self.addSeparator()
        self.addAction(_create_action(self, MenuAction.RELOAD.value, self.raise_event,
                                      icon=QIcon.fromTheme("view-refresh"), data=MenuAction.RELOAD))

    def raise_event(self, event, arg):
        app.logger.debug(f"{event} -> {arg}")
        self.menu_event.emit(event, arg)


class MenuBar(QMenuBar):
    menu_event = pyqtSignal(MenuAction, object)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        file_menu = QMenu("&File", self)
        file_menu.addAction(_create_action(self, MenuAction.OPEN.value, self.raise_event,
                                           icon=QIcon.fromTheme("document-open"),
                                           shortcut="Ctrl+O", data=MenuAction.OPEN))

        file_menu.addMenu(self._create_recent_list())

        file_menu.addSeparator()
        file_menu.addAction(_create_action(self, MenuAction.EXIT.value, self.raise_event,
                                           icon=QIcon.fromTheme("application-exit"),
                                           shortcut="Ctrl+Q", data=MenuAction.EXIT))

        view_menu = QMenu("&View", self)
        view_menu.addAction(_create_action(self, MenuAction.SEARCH.value, self.raise_event,
                                           icon=QIcon.fromTheme("edit-find"),
                                           shortcut="Ctrl+F", data=MenuAction.SEARCH))
        file_menu.addSeparator()
        view_menu.addAction(_create_action(self, MenuAction.EXPAND.value, self.raise_event,
                                           icon=QIcon.fromTheme("list-add"),
                                           shortcut="Ctrl+E", data=MenuAction.EXPAND))
        view_menu.addAction(_create_action(self, MenuAction.COLLAPSE.value, self.raise_event,
                                           icon=QIcon.fromTheme("list-remove"),
                                           shortcut="Ctrl+C", data=MenuAction.COLLAPSE))
        view_menu.addAction(_create_action(self, MenuAction.TOP.value, self.raise_event,
                                           icon=QIcon.fromTheme("go-top"),
                                           shortcut="Home", data=MenuAction.TOP))
        view_menu.addAction(_create_action(self, MenuAction.BOTTOM.value, self.raise_event,
                                           icon=QIcon.fromTheme("go-bottom"),
                                           shortcut="End", data=MenuAction.BOTTOM))
        view_menu.addSeparator()
        view_menu.addMenu(self._create_color_theme_menu())
        view_menu.addAction(_create_action(self, MenuAction.ATTRIBUTES.value, self.raise_event,
                                           data=MenuAction.ATTRIBUTES,
                                           checked=AppSettings.show_attributes()))
        view_menu.addAction(_create_action(self, MenuAction.FONT.value, self.raise_event,
                                           icon=QIcon.fromTheme("preferences-desktop-font"),
                                           data=MenuAction.FONT))

        help_menu = QMenu("&Help", self)
        help_menu.addAction(_create_action(self, MenuAction.ABOUT.value, self.raise_event,
                                           icon=QIcon.fromTheme("help-about"),
                                           tooltip="About this application", data=MenuAction.ABOUT))

        self.addMenu(file_menu)
        self.addMenu(view_menu)
        self.addMenu(help_menu)

    def _create_recent_list(self):
        recent_menu = QMenu("Recent Files", self)
        recent_files = AppSettings.get_recent_files()
        if recent_files is not None:
            for file in recent_files:
                action = _create_action(self, file, self.raise_event, data=MenuAction.RECENT, argument=file)
                recent_menu.addAction(action)
        return recent_menu

    def _create_color_theme_menu(self):
        color_menu = QMenu("Color Theme", self)
        color_theme = AppSettings.color_theme()
        for color in color_theme:
            pixmap = QPixmap(48, 48)
            pixmap.fill(QColor(color_theme[color]))
            action = _create_action(self, color.title(), self.raise_event, data=MenuAction.COLOR, argument=color,
                                    icon=QIcon(pixmap))
            color_menu.addAction(action)
        return color_menu

    def raise_event(self, data, argument):
        app.logger.debug(f"{data} -> {argument}")
        self.menu_event.emit(data, argument)


def _create_action(parent, name, func, data, shortcut=None, tooltip=None, icon=None, checked=None, argument=None):
    action = QAction(name, parent)
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tooltip is not None:
        if shortcut is not None:
            tooltip = f"{tooltip} ({shortcut})"
        action.setToolTip(tooltip)
    if data is not None:
        action.triggered.connect(partial(func, data, argument))
    if icon is not None:
        action.setIcon(icon)
    if checked is not None:
        action.setCheckable(True)
        action.setChecked(checked)
    return action
