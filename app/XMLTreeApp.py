import os.path
import sys
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel, QMessageBox, QFontDialog, QColorDialog

import app
from app import AppSettings
from app.XMLTreeView import XMLTreeView, XMLSearch
from app.Menu import MenuBar, MenuAction, XMLTreeViewContextMenu


class XMLTreeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.XML_tree = XMLTreeView()
        self.XML_search = XMLSearch()
        self.context_menu = XMLTreeViewContextMenu()
        self.init_ui()

    def init_ui(self):
        menubar = MenuBar()
        menubar.menu_event.connect(self.menu_event)
        self.setMenuBar(menubar)

        self.context_menu.menu_event.connect(self.menu_event)

        self.XML_tree.path_changed_event.connect(self.path_changed_event)
        self.XML_tree.xml_load_event.connect(self.timed_message_event)
        self.XML_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.XML_tree.customContextMenuRequested.connect(self.context_menu_requested)
        self.setCentralWidget(self.XML_tree)

        self.XML_search.search_change_event.connect(self.search_criteria_change_event)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.XML_search)

        self.setMinimumSize(800, 1024)
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

    def menu_event(self, menu_action, argument):
        def load_file(_file):
            self.XML_tree.set_file(_file)
            self.timed_message_event("Attempting to lad file. Please wait")
            self.setWindowTitle(f"{app.__APP_NAME__} - {os.path.basename(_file)}")

        if menu_action == MenuAction.OPEN:
            file, _ = QFileDialog.getOpenFileUrl(caption="Select an XML File",
                                                 filter='Extensible Markup Language (XML) file(*.xml)')
            if not file.isEmpty():
                load_file(file.toLocalFile())
        if menu_action == MenuAction.RECENT:
            load_file(argument)

        elif menu_action == MenuAction.SEARCH:
            if self.XML_search.isVisible():
                self.XML_search.hide()
            else:
                self.XML_search.show()
        elif menu_action == MenuAction.EXPAND:
            selected = self.XML_tree.selectedIndexes()
            if len(selected):
                self.XML_tree.expandRecursively(selected[0], depth=-1)
            else:
                self.timed_message_event("Nothing selected to expand!")
        elif menu_action == MenuAction.COLLAPSE:
            selected = self.XML_tree.selectedIndexes()
            if len(selected):
                self.XML_tree.collapse(selected[0])
            else:
                self.timed_message_event("Nothing selected to collapse!")
        elif menu_action == MenuAction.TOP:
            self.XML_tree.scrollToTop()
        elif menu_action == MenuAction.BOTTOM:
            self.XML_tree.scrollToBottom()
        elif menu_action == MenuAction.ATTRIBUTES:
            AppSettings.set_show_attributes(not AppSettings.show_attributes())
            self.XML_tree.reload()
        elif menu_action == MenuAction.FONT:
            _font, ok = QFontDialog.getFont(self.XML_tree.font(), self, "Select Font")
            if ok:
                self.XML_tree.setFont(_font)
                AppSettings.set_font(self.XML_tree.font())
                self.XML_tree.reload()
        elif menu_action == MenuAction.COLOR:
            theme = AppSettings.color_theme()
            current = theme[argument]
            _color = QColorDialog.getColor(initial=QColor(current), parent=self,
                                           title=f"Select color for {argument.title()}",
                                           options=QColorDialog.ShowAlphaChannel)
            if _color.isValid():
                theme[argument] = _color.name()
                AppSettings.set_color_theme(theme)
                self.XML_tree.reload()

        elif menu_action == MenuAction.HIDE:
            selected = self.XML_tree.selectedIndexes()
            for item in selected:
                self.XML_tree.model.removeRow(item.row(), item.parent())
        elif menu_action == MenuAction.RELOAD:
            self.XML_tree.reload()
        elif menu_action == MenuAction.EXIT:
            self.close()
        elif menu_action == MenuAction.ABOUT:
            with open(os.path.join(os.path.dirname(__file__), "../resources/about.html"), 'r') as file:
                about_html = file.read()
            QMessageBox.about(self, app.__APP_NAME__, about_html.format(APP_NAME=app.__APP_NAME__,
                                                                        VERSION=app.__VERSION__,
                                                                        YEAR=datetime.now().year))

    def context_menu_requested(self, point):
        index = self.XML_tree.indexAt(point)
        item = self.XML_tree.model.itemFromIndex(index)
        if item is not None:
            self.context_menu.exec_(self.XML_tree.mapToGlobal(point))


def main():
    app = QApplication(sys.argv)
    _ = XMLTreeApp()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
