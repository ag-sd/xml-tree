import os.path
import os.path
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QApplication, QMainWindow

import app
from app import AppSettings
from app.AppSettings import SettingsKeys
from app.Menu import MenuAction, XMLTreeViewContextMenu, MenuHandler
from app.XMLTreeView import XMLTreeView


class XMLTreeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.XML_tree = XMLTreeView()
        self.context_menu = XMLTreeViewContextMenu()
        self.menu_handler = MenuHandler(self, self.XML_tree)
        self.init_ui()

    def init_ui(self):
        self.menu_handler.load_file_event.connect(self.load_file_event)
        self.setMenuBar(self.menu_handler.menubar)
        AppSettings.settings.settings_change_event.connect(self.settings_change_event)

        self.XML_tree.path_changed_event.connect(self.path_changed_event)
        self.XML_tree.xml_load_event.connect(self.timed_message_event)
        self.XML_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.XML_tree.customContextMenuRequested.connect(self.context_menu_requested)
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

    def settings_change_event(self, setting, value):
        match setting:
            case SettingsKeys.toggle_attributes | SettingsKeys.syntax_highlighting:
                self.XML_tree.reload()
            case SettingsKeys.font:
                _font = QFont()
                if _font.fromString(value):
                    self.XML_tree.setFont(_font)
                    self.XML_tree.reload()

    def menu_event(self, menu_action, argument):
        if menu_action == MenuAction.SEARCH:
            if self.XML_search.isVisible():
                self.XML_search.hide()
            else:
                self.XML_search.show()
        elif menu_action == MenuAction.HIDE:
            sorted_to_delete = self._get_models_sorted_by_ancestry(self.XML_tree.selectedIndexes())
            for item in sorted_to_delete:
                self.XML_tree.model.removeRow(item.row(), item.parent())

    def context_menu_requested(self, point):
        index = self.XML_tree.indexAt(point)
        item = self.XML_tree.model.itemFromIndex(index)
        if item is not None:
            self.menu_handler.menucontext.exec_(self.XML_tree.mapToGlobal(point))

    @staticmethod
    def _get_models_sorted_by_ancestry(model_indices):
        ancestries = []
        max_len = 0
        # For each selection
        for item in model_indices:
            ancestry = []
            tmp = item
            # Create its path
            while tmp.parent().row() >= 0:
                ancestry.insert(0, tmp.row())
                tmp = tmp.parent()
            # And pad it with zeros
            if len(ancestry) > max_len:
                max_len = len(ancestry)
            ancestries.append((item, ancestry))
        # And pad it with zeros
        for i in range(0, len(ancestries)):
            ancestries[i] = (ancestries[i][0], ancestries[i][1] + [0] * (max_len - len(ancestries[i][1])))
        # Sort these in reverse order
        for i in range(max_len - 1, -1, -1):
            ancestries.sort(key=lambda x: x[1][i], reverse=True)

        return [element[0] for element in ancestries]


def main():
    app = QApplication(sys.argv)
    _ = XMLTreeApp()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
