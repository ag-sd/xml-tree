import os.path
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel

import app
from app.XMLTreeView import XMLTreeView, XMLSearch
from app.Menu import MenuBar, MenuAction


class XMLTreeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.XML_tree = XMLTreeView()
        self.XML_search = XMLSearch()
        self.x_path = QLabel("XPath: ")
        self.init_ui()

    def init_ui(self):
        menubar = MenuBar()
        menubar.menu_event.connect(self.menu_event)
        self.setMenuBar(menubar)

        self.XML_tree.path_changed_event.connect(self.path_changed_event)
        self.XML_tree.xml_load_event.connect(self.timed_message_event)
        self.setCentralWidget(self.XML_tree)

        self.XML_search.search_change_event.connect(self.search_criteria_change_event)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.XML_search)

        self.statusBar().addPermanentWidget(self.x_path)

        self.setMinimumSize(800, 1024)
        self.setWindowTitle(app.__APP_NAME__)
        self.setWindowIcon(QIcon.fromTheme("text-x-generic-template"))

        self.XML_tree.set_file("/mnt/Dev/test/part.XML")
        self.show()

    def path_changed_event(self, path):
        self.statusBar().showMessage(path)

    def timed_message_event(self, message):
        self.statusBar().showMessage(message, msecs=5000)

    def search_criteria_change_event(self, criteria):
        self.timed_message_event("Searching...")
        self.XML_tree.search(criteria)

    def menu_event(self, menu_action):
        if menu_action == MenuAction.OPEN:
            file, _ = QFileDialog.getOpenFileUrl(caption="Select an XML File",
                                                 filter='Extensible Markup Language (XML) file(*.xml)')
            if not file.isEmpty():
                self.XML_tree.model.clear()
                self.XML_tree.set_file(file.toLocalFile())
                self.setWindowTitle(f"{app.__APP_NAME__} : {os.path.basename(file.toLocalFile())}")


def main():
    app = QApplication(sys.argv)
    _ = XMLTreeApp()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
