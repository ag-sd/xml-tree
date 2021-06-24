import sys
from xml.etree import ElementTree

from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QTreeView, QApplication


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
        # TODO ADD Back self.clear()
        # TODO replace with defusedxml: https://pypi.org/project/defusedxml
        self._build_tree(self.invisibleRootItem(), ElementTree.parse(self.xml_file).getroot())

    @staticmethod
    def _build_tree(parent, root):
        if len(root):
            section_root = XMLViewModel._create_node(root.tag, root.attrib, XMLViewModel.__ROOT_ICON)
            parent.appendRow(section_root)
            # Else for each child recurse
            for child in root:
                XMLViewModel._build_tree(section_root, child)
        else:
            # If node has no children return
            parent.appendRow(
                XMLViewModel._create_node(f"{root.tag} = {root.text}", root.attrib, XMLViewModel.__NODE_ICON))

    @staticmethod
    def _create_node(text, attributes, icon):
        text = XMLViewModel._clean_text(text)
        formatted_attributes = XMLViewModel._format_attributes(attributes)
        if formatted_attributes:
            text = f"{text}  {formatted_attributes}"
        node = QStandardItem(text)
        node.setIcon(icon)
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
    def __init__(self):
        super().__init__()
        self.model = XMLViewModel()
        self.init_ui()

    def init_ui(self):
        self.setEditTriggers(QTreeView.NoEditTriggers)
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setWordWrap(True)
        self.setHeaderHidden(True)

    def set_file(self, file):
        self.model = XMLViewModel(file)
        self.setModel(self.model)


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
