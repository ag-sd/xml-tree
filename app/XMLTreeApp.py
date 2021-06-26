import os.path
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel

import app
from app.XMLTreeView import XMLTreeView
from app.MenuBar import MenuBar, MenuAction


class XMLTreeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.XML_tree = XMLTreeView()
        self.x_path = QLabel("XPath: ")
        self.init_ui()

    def init_ui(self):
        menubar = MenuBar()
        menubar.menu_event.connect(self.menu_event)
        self.setMenuBar(menubar)

        self.XML_tree.path_changed_event.connect(self.path_changed_event)
        self.setCentralWidget(self.XML_tree)

        self.statusBar().addPermanentWidget(self.x_path)

        self.setMinimumSize(800, 1024)
        self.setWindowTitle(app.__APP_NAME__)
        self.setWindowIcon(QIcon.fromTheme("text-x-generic-template"))

        self.show()

    def path_changed_event(self, path):
        self.x_path.setText(path)

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
