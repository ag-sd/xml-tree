import os
from datetime import datetime
from enum import Enum
from functools import partial

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QPixmap, QColor
from PyQt5.QtWidgets import QMenuBar, QAction, QMenu, QFileDialog, QFontDialog, QColorDialog, QMessageBox

import app
from app import AppSettings


class MenuAction(Enum):
    OPEN = "Open ..."
    RECENT = "Recent Files"
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
                                      icon=QIcon.fromTheme("edit-delete"), data=MenuAction.HIDE,
                                      shortcut="Delete"))
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
        AppSettings.settings.settings_change_event.connect(self.settings_changed)

    def init_ui(self):
        file_menu = QMenu("&File", self)
        file_menu.addAction(_create_action(self, MenuAction.OPEN.value, self.raise_event,
                                           icon=QIcon.fromTheme("document-open"),
                                           shortcut="Ctrl+O", data=MenuAction.OPEN))

        # file_menu.addMenu(self._create_recent_list())
        file_menu.addMenu(QMenu(MenuAction.RECENT.value, self))

        file_menu.addSeparator()
        file_menu.addAction(_create_action(self, MenuAction.EXIT.value, self.raise_event,
                                           icon=QIcon.fromTheme("application-exit"),
                                           shortcut="Ctrl+Q", data=MenuAction.EXIT))

        view_menu = QMenu("&View", self)
        view_menu.addAction(_create_action(self, MenuAction.SEARCH.value, self.raise_event,
                                           icon=app.theme_icon_with_fallback("edit-find"),
                                           shortcut="Ctrl+F", data=MenuAction.SEARCH))
        file_menu.addSeparator()
        view_menu.addAction(_create_action(self, MenuAction.EXPAND.value, self.raise_event,
                                           icon=QIcon.fromTheme("list-add"),
                                           shortcut="Ctrl+E", data=MenuAction.EXPAND))
        view_menu.addAction(_create_action(self, MenuAction.COLLAPSE.value, self.raise_event,
                                           icon=QIcon.fromTheme("list-remove"),
                                           shortcut="Ctrl+C", data=MenuAction.COLLAPSE))
        view_menu.addAction(_create_action(self, MenuAction.HIDE.value, self.raise_event,
                                           icon=QIcon.fromTheme("edit-delete"), data=MenuAction.HIDE,
                                           shortcut="Delete"))
        view_menu.addAction(_create_action(self, MenuAction.TOP.value, self.raise_event,
                                           icon=QIcon.fromTheme("go-top"),
                                           shortcut="Home", data=MenuAction.TOP))
        view_menu.addAction(_create_action(self, MenuAction.BOTTOM.value, self.raise_event,
                                           icon=QIcon.fromTheme("go-bottom"),
                                           shortcut="End", data=MenuAction.BOTTOM))
        view_menu.addSeparator()
        view_menu.addMenu(QMenu(MenuAction.COLOR.value, self))
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
        self.update_color_theme_menu()
        self.update_recent_list()

    def update_recent_list(self):
        recent_menu = self._find_action(MenuAction.RECENT.value, self.actions()).menu()
        recent_menu.clear()
        recent_files = AppSettings.get_recent_files()
        if recent_files is not None:
            for file in recent_files:
                action = _create_action(self, file, self.raise_event, data=MenuAction.RECENT, argument=file)
                recent_menu.addAction(action)
        return recent_menu

    def settings_changed(self, setting, _):
        if setting == AppSettings.SettingsKeys.syntax_highlighting:
            self.update_color_theme_menu()

    def update_color_theme_menu(self):
        color_theme_menu = self._find_action(MenuAction.COLOR.value, self.actions()).menu()
        color_theme = AppSettings.color_theme()
        for color in color_theme:
            pixmap = QPixmap(48, 48)
            pixmap.fill(QColor(color_theme[color]))
            action = self._find_action(color.title(), color_theme_menu.actions())
            if action is None:
                action = _create_action(self, color.title(), self.raise_event, data=MenuAction.COLOR, argument=color,
                                        icon=QIcon(pixmap))
                color_theme_menu.addAction(action)
            else:
                action.setIcon(QIcon(pixmap))

    @staticmethod
    def _find_action(text, actions):
        """
        BFS search of the menu for a particular action. Caller can cast it to a menu if required
        :param text: action text to search for
        :return:
        """
        q = list(actions)
        while len(q) > 0:
            action = q.pop(0)
            if action.isSeparator():
                continue
            if action.text() == text:
                return action
            if action.menu() is not None:
                q.extend(action.menu().actions())

    def raise_event(self, data, argument):
        app.logger.debug(f"{data} -> {argument}")
        self.menu_event.emit(data, argument)


class MenuHandler(QObject):
    load_file_event = pyqtSignal(str)

    def __init__(self, mainapp, treeview):
        super(MenuHandler, self).__init__()
        self.mainapp = mainapp
        self.treeview = treeview
        self.menubar = MenuBar()
        self.menucontext = XMLTreeViewContextMenu()
        self.menubar.menu_event.connect(self.menu_event)
        self.menucontext.menu_event.connect(self.menu_event)

    def menu_event(self, menu_action, argument):
        match menu_action:
            #   #   #   #   #   #   #   #   #
            #   Application Menu Actions    #
            #   #   #   #   #   #   #   #   #
            case MenuAction.OPEN:
                file, _ = QFileDialog.getOpenFileUrl(parent=self.mainapp, caption="Select an XML File",
                                                     filter="XML files (*.xml);;JSON files (*.json)")
                if not file.isEmpty():
                    self.load_file_event.emit(file.toLocalFile())
            case MenuAction.RECENT:
                file = argument
                if os.path.exists(file):
                    # Move it to the bottom of the list
                    AppSettings.add_to_recent(file)
                    self.load_file_event.emit(argument)
                else:
                    app.logger.warn(f"{file} was not found, removing it from recents list")
                    AppSettings.remove_from_recent(file)
                self.menubar.update_recent_list()
            case MenuAction.ATTRIBUTES:
                AppSettings.set_show_attributes(not AppSettings.show_attributes())
            case MenuAction.FONT:
                _font, ok = QFontDialog.getFont(AppSettings.font(), parent=self.mainapp, caption="Select Font")
                if ok:
                    AppSettings.set_font(_font)
            case MenuAction.COLOR:
                theme = AppSettings.color_theme()
                current = theme[argument]
                _color = QColorDialog.getColor(initial=QColor(current), parent=self.mainapp,
                                               title=f"Select color for {argument.title()}",
                                               options=QColorDialog.ShowAlphaChannel)
                if _color.isValid():
                    theme[argument] = _color.name()
                    AppSettings.set_color_theme(theme)
            case MenuAction.ABOUT:
                with open(os.path.join(os.path.dirname(__file__), "../resources/about.html"), 'r') as file:
                    about_html = file.read()
                QMessageBox.about(self.mainapp, app.__APP_NAME__, about_html.format(APP_NAME=app.__APP_NAME__,
                                                                                    VERSION=app.__VERSION__,
                                                                                    YEAR=datetime.now().year))
            case MenuAction.EXIT:
                self.mainapp.close()

            #   #   #   #   #   #   #   #
            #   Context Menu Actions    #
            #   #   #   #   #   #   #   #
            case MenuAction.EXPAND:
                selected = self.treeview.selectedIndexes()
                if len(selected):
                    self.treeview.expandRecursively(selected[0], depth=-1)
            case MenuAction.COLLAPSE:
                selected = self.treeview.selectedIndexes()
                if len(selected):
                    self.treeview.collapse(selected[0])
            case MenuAction.TOP:
                self.treeview.scrollToTop()
            case MenuAction.BOTTOM:
                self.treeview.scrollToBottom()
            case MenuAction.RELOAD:
                self.treeview.reload()

            case _:
                app.logger.error(f"Unexpected menu action {menu_action}")


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
