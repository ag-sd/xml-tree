import os
import sys
from lxml import etree

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QTreeView, QApplication

import app


class XMLViewModel(QStandardItemModel):
    __ROOT_ICON = QIcon.fromTheme("folder")
    __NODE_ICON = QIcon.fromTheme("text-x-generic")

    def __init__(self, xml_file=None):
        super().__init__()
        self.xml_file = xml_file

        if xml_file:
            self.reload()

    def set_xml_file(self, xml_file):
        self.xml_file = xml_file

    def reload(self):
        # TODO replace with defusedxml: https://pypi.org/project/defusedxml
        # TODO validate XML before load
        self.clear()
        app.logger.debug("Starting load")
        xml = etree.parse(self.xml_file).getroot()
        app.logger.debug("Parsed XML, building tree")
        self._build_tree(etree.ElementTree(xml), self.invisibleRootItem(), xml)
        app.logger.debug("Tree built")


    @staticmethod
    def _build_tree(tree, parent_item, current_xml_node):
        section_root = XMLViewModel._create_tv_item(current_xml_node, tree.getpath(current_xml_node))
        parent_item.appendRow(section_root)
        for child in current_xml_node:
            XMLViewModel._build_tree(tree, section_root, child)

    @staticmethod
    def _create_tv_item(current_xml_node, _path):
        if len(current_xml_node):
            return XMLViewModel._create_node(
                current_xml_node.tag, current_xml_node.attrib, XMLViewModel.__ROOT_ICON, _path)
        else:
            return XMLViewModel._create_node(
                f"{current_xml_node.tag} = {current_xml_node.text}",
                current_xml_node.attrib, XMLViewModel.__NODE_ICON, _path)

    @staticmethod
    def _create_node(text, attributes, icon, _path):
        text = XMLViewModel._clean_text(text)
        formatted_attributes = XMLViewModel._format_attributes(attributes)
        if formatted_attributes:
            text = f"{text}  {formatted_attributes}"
        node = QStandardItem(text)
        node.setIcon(icon)
        node.setData(_path, Qt.UserRole)
        return node

    @staticmethod
    def _clean_text(text):
        if text is None:
            return None

        if text.find("\n") > 0:
            text = text.replace("\n", " ")
        return text.strip()

    @staticmethod
    def _format_attributes(attributes):
        if not len(attributes):
            return None
        text = "[ "

        for key in attributes:
            text = text + f"{key}=\"{attributes[key]}\""

        return text + " ]"


class XMLTreeView(QTreeView):
    path_changed_event = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.model = XMLViewModel()
        self.init_ui()

    def init_ui(self):
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setEditTriggers(QTreeView.NoEditTriggers)
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setWordWrap(True)
        self.setHeaderHidden(True)

    def set_file(self, file):
        if os.path.exists(file) and os.path.isfile(file):
            self.model = XMLViewModel(file)
            self.setModel(self.model)
        else:
            app.logger.debug(f"{file} is not a valid path")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            file = event.mimeData().urls()[0].toLocalFile()
            self.set_file(file)
        else:
            event.ignore()

    def currentChanged(self, current, _):
        item = self.model.itemFromIndex(current)
        if item is not None:
            self.path_changed_event.emit(item.data(Qt.UserRole))


def main():
    app = QApplication(sys.argv)
    ex = XMLTreeView()
    ex.set_file("/mnt/Dev/test/nasa.xml")
    ex.show()
    sys.exit(app.exec_())

    # model = XMLViewModel()
    # model.set_xml_file("/mnt/Dev/test/nasa.xml")
    # model.reload()


if __name__ == '__main__':
    main()
