from enum import Enum
from functools import partial

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMenuBar, QAction, QMenu

import app


class MenuAction(Enum):
    OPEN = "Open"
    EXPAND = "Expand" #all children"


class XMLTreeViewContextMenu(QMenu):
    menu_event = pyqtSignal(MenuAction)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.addAction(_create_action(self, MenuAction.EXPAND.value, self.raise_event,
                                      icon=QIcon.fromTheme("list-add")))

    def raise_event(self, event):
        app.logger.debug(event)
        self.menu_event.emit(MenuAction(event))


class MenuBar(QMenuBar):
    menu_event = pyqtSignal(MenuAction)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        file_menu = QMenu("&File", self)
        file_menu.addAction(_create_action(self, MenuAction.OPEN.value, self.raise_event,
                                           icon=QIcon.fromTheme("document-open")))

        self.addMenu(file_menu)

    def raise_event(self, event):
        app.logger.debug(event)
        self.menu_event.emit(MenuAction(event))


def _create_action(parent, name, func, shortcut=None, tooltip=None, icon=None, checked=None):
    action = QAction(name, parent)
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tooltip is not None:
        if shortcut is not None:
            tooltip = f"{tooltip} ({shortcut})"
        action.setToolTip(tooltip)
    action.triggered.connect(partial(func, name))
    if icon is not None:
        action.setIcon(icon)
    if checked is not None:
        action.setCheckable(True)
        action.setChecked(checked)
    return action