import os.path
import os.path
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QApplication, QMainWindow

import app
from app import AppSettings
from app.AppSettings import SettingsKeys
from app.Menu import XMLTreeViewContextMenu, MenuHandler
from app.XMLDataViews import XMLTreeView, PropertyPanel


class XMLTreeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.XML_tree = XMLTreeView()
        self.property_panel = PropertyPanel(self)
        self.context_menu = XMLTreeViewContextMenu()
        self.menu_handler = MenuHandler(self, self.XML_tree)
        self.init_ui()

    def init_ui(self):
        self.menu_handler.load_file_event.connect(self.load_file_event)
        self.menu_handler.tabulate_event.connect(self.tabulate_event)
        self.setMenuBar(self.menu_handler.menubar)
        AppSettings.settings.settings_change_event.connect(self.settings_change_event)

        self.property_panel.item_doubleclicked.connect(self.table_item_clicked)

        self.XML_tree.path_changed_event.connect(self.path_changed_event)
        self.XML_tree.xml_load_event.connect(self.timed_message_event)
        self.XML_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.XML_tree.customContextMenuRequested.connect(self.context_menu_requested)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.property_panel)
        self.setCentralWidget(self.XML_tree)

        self.setMinimumSize(640, 480)
        self.setWindowTitle(app.__APP_NAME__)
        self.setWindowIcon(QIcon.fromTheme("text-x-generic-template"))

        self.show()

    def path_changed_event(self, path):
        self.statusBar().showMessage(path)

    def timed_message_event(self, message):
        self.statusBar().showMessage(message, msecs=5000)

    def search_criteria_change_event(self, criteria):
        search_message = self.XML_tree.search(criteria)
        app.logger.debug(search_message)
        self.timed_message_event(search_message)

    def load_file_event(self, _file):
        self.XML_tree.set_file(_file)
        self.timed_message_event("Attempting to load file. Please wait")
        self.setWindowTitle(f"{app.__APP_NAME__} - {os.path.basename(_file)}")

    def tabulate_event(self, parent_index, data):
        self.property_panel.tabulate(parent_index, data)

    def table_item_clicked(self, parent_index, item_index, item_name):
        self.XML_tree.show_node(parent_index, item_index, item_name)

    def search_event(self):
        if self.XML_search.isVisible():
            self.XML_search.hide()
        else:
            self.XML_search.show()

    def settings_change_event(self, setting, value):
        match setting:
            case SettingsKeys.toggle_attributes | SettingsKeys.syntax_highlighting:
                self.XML_tree.reload()
            case SettingsKeys.font:
                _font = QFont()
                if _font.fromString(value):
                    self.XML_tree.setFont(_font)
                    self.XML_tree.reload()

    def context_menu_requested(self, point):
        index = self.XML_tree.indexAt(point)
        item = self.XML_tree.treemodel.itemFromIndex(index)
        if item is not None:
            self.menu_handler.request_context_menu(self.XML_tree.mapToGlobal(point), item.can_tabulate())


def main():
    app = QApplication(sys.argv)
    _ = XMLTreeApp()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
