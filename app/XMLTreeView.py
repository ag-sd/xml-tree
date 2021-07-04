import datetime
import os
import sys
import typing

from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QSize, QItemSelectionModel, QVariant
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon, QTextDocument, QColor
from PyQt5.QtWidgets import QTreeView, QApplication, QDockWidget, QLineEdit, QPushButton, QCheckBox, QHBoxLayout, \
    QVBoxLayout, QGroupBox, QComboBox, QStyledItemDelegate, QStyleOptionViewItem, QStyle, QAbstractItemView
from lxml import etree

import app
from app import AppSettings

_SEARCH_CRITERIA = {
        "Contains": Qt.MatchContains,
        "Exact Match": Qt.MatchFixedString,
        "Starts With": Qt.MatchStartsWith,
        "Ends With": Qt.MatchEndsWith,
        "Regular Expression": Qt.MatchRegularExpression,
        "Wild Card": Qt.MatchWildcard
    }


class XMLStandardItem(QStandardItem):
    __ROOT_ICON = QIcon.fromTheme("folder")
    __NODE_ICON = QIcon.fromTheme("text-x-generic")

    def __init__(self, node):
        super().__init__()
        self.node = node
        self.display_text = None
        self.html_text = None
        self.highlight = False
        self.colors = AppSettings.color_theme()
        self._create_display_texts()

    def data(self, role: int = Qt.UserRole + 1) -> typing.Any:
        if role == Qt.BackgroundColorRole and self.highlight:
            return QVariant(QColor(self.colors["highlight"]))
        return QStandardItem.data(self, role)

    def _create_display_texts(self):
        if len(self.node):
            text = self._clean_text(self.node.tag)
            html = f"<p><span style='color:{self.colors['node']};'>{text}</span></p>"
            self.setIcon(self.__ROOT_ICON)
        elif self.node.tag is etree.Comment:
            text = self._clean_text(f"#  {self.node.text}")
            html = f"<i style='color:{self.colors['comment']};'>{text}</i>"
        else:
            key = self._clean_text(self.node.tag)
            value = self._clean_text(self.node.text)
            text = f"{key} = {value}"
            html = f"<p>" \
                   f"<span style='color:{self.colors['key']};'>{key}</span>" \
                   f" = " \
                   f"<span style='color:{self.colors['value']};'>{value}</span>" \
                   f"</p>"
            self.setIcon(self.__NODE_ICON)

        if AppSettings.show_attributes():
            attr_text, attr_html = self._format_attributes(self.node.attrib)
            if attr_text:
                text = text.replace("</p>", f"  {attr_text}</p>")
                html = html.replace("</p>", f"  {attr_html}</p>")
        self.html_text = html
        self.setText(text)

    def _format_attributes(self, attributes):
        if not len(attributes):
            return None, None
        text = "[ "
        html = "[ "

        for key in attributes:
            text = text + f"{key}=\"{attributes[key]}\""
            html = html + f"<i>{key}</i> = " \
                          f"<b><span style='color:{self.colors['attribute']};'>" \
                          f"\"{attributes[key]}\"</span></b> "

        return text + " ]", html + " ]"

    @staticmethod
    def _clean_text(text):
        if text is None:
            return None
        # if text.find("\n") > 0:
        #     text = text.replace("\n", " ")
        return text.strip()


class XMLViewModel(QStandardItemModel):

    xml_load_event = pyqtSignal(str)

    def __init__(self, xml_file=None):
        super().__init__()
        self.xml_file = xml_file
        self.etree = None

        if xml_file:
            self.reload()

    def set_xml_file(self, xml_file):
        self.xml_file = xml_file

    def reload(self):
        start_time = datetime.datetime.now()
        try:
            app.logger.debug("Starting load")
            _, ext = os.path.splitext(self.xml_file)
            if ext.upper().startswith(".HTM"):
                app.logger.debug("This is an HTML file")
                parser = etree.HTMLParser()
            elif ext.upper() == ".XML":
                app.logger.debug("This is an HTML file")
                parser = etree.XMLParser()
            else:
                app.logger.debug("This is an Unsupported file. It cannot be loaded")
                raise Exception("This is an unsupported file. Only HTML and XML files permitted")

            xml = etree.parse(self.xml_file, parser=parser).getroot()
            self.etree = etree.ElementTree(xml)
            parse_end_time = datetime.datetime.now() - start_time
            app.logger.debug("Parsed XML, building tree")
            AppSettings.add_to_recent(self.xml_file)
        except Exception as e:
            message = f"Error while loading file {str(e)}"
            self.xml_load_event.emit(message)
            app.logger.error(message)
            return

        self.clear()
        self._build_tree(self.etree, self.invisibleRootItem(), xml)
        app.logger.debug("Tree built")
        total_time = datetime.datetime.now() - start_time
        self.xml_load_event.emit(f"File Loaded in {total_time.total_seconds()} seconds. "
                                 f"(Took {parse_end_time.total_seconds()} seconds to parse)")

    def get_xpath(self, xml_node):
        return self.etree.getpath(xml_node)

    @staticmethod
    def _build_tree(tree, parent_item, current_xml_node):
        section_root = XMLStandardItem(current_xml_node)
        parent_item.appendRow(section_root)
        for child in current_xml_node:
            XMLViewModel._build_tree(tree, section_root, child)


class XMLItemDelegate(QStyledItemDelegate):
    # https://www.qtcentre.org/threads/22863-HTML-and-QStandardItem
    # https://www.qtcentre.org/threads/5548-QStandardItem-subpart-of-the-text-as-bold
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def paint(self, painter, option, index):
        item = self.parent.model.itemFromIndex(index)

        options = QStyleOptionViewItem()
        options.__init__(option)
        self.initStyleOption(options, index)
        options.textElideMode = Qt.ElideRight

        painter.save()

        doc = QTextDocument()
        doc.setHtml(item.html_text)

        # get focus rect and selection background
        options.text = ""
        options.widget.style().drawControl(QStyle.CE_ItemViewItem, options, painter)

        # draw using our rich text document
        if options.features & QStyleOptionViewItem.HasDecoration != QStyleOptionViewItem.HasDecoration:
            # This item has no decorations
            painter.translate(options.rect.left(), options.rect.top())
        else:
            painter.translate(options.rect.left() + option.decorationSize.width(), options.rect.top())
        rect = QRectF()
        rect.__init__(0, 0, options.rect.width(), options.rect.height())
        doc.drawContents(painter, rect)

        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem()
        options.__init__(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        size = QSize()
        size.__init__(doc.idealWidth(), doc.size().height())
        return size


class XMLTreeView(QTreeView):
    path_changed_event = pyqtSignal(str)
    xml_load_event = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.model = XMLViewModel()
        self.current_search = []
        self.init_ui()

    def init_ui(self):
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setEditTriggers(QTreeView.NoEditTriggers)
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setWordWrap(True)
        self.setHeaderHidden(True)
        self.setItemDelegate(XMLItemDelegate(parent=self))
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # with open(os.path.join(os.path.dirname(__file__), "../resources/tree.colortheme.css"), 'r') as file:
        #     self.setStyleSheet(file.read())
        _font = AppSettings.font()
        if _font is not None:
            self.setFont(_font)

    def set_file(self, file):
        if os.path.exists(file) and os.path.isfile(file):
            app.logger.debug(f"Attempting to load {file}")
            self.model = XMLViewModel(file)
            self.model.xml_load_event.connect(self.model_xml_load_event)
            self.setModel(self.model)
            self.current_search.clear()
        else:
            app.logger.debug(f"{file} is not a valid path")

    def reload(self):
        self.model.beginResetModel()
        self.model.reload()
        self.model.endResetModel()

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
            self.model.get_xpath(item.node)
            self.path_changed_event.emit(self.model.get_xpath(item.node))

    def model_xml_load_event(self, message):
        self.xml_load_event.emit(message)

    def search(self, criteria):
        self.setUpdatesEnabled(False)
        result_message = "0 results found"
        # clear previous results:
        for row in self.current_search:
            row.highlight = False
            row.emitDataChanged()

        app.logger.debug(f"Search for {criteria}")
        self.selectionModel().clear()
        self.current_search = self.model.findItems(criteria.text, criteria.options)
        if len(self.current_search):
            match_number = criteria.match_count % len(self.current_search)
            match_index = self.current_search[match_number].index()
            for row in self.current_search:
                row.highlight = criteria.highlight
                row.emitDataChanged()

            self.selectionModel().select(match_index, QItemSelectionModel.ClearAndSelect)
            self.scrollTo(match_index)
            result_message = f"Showing result {match_number + 1} of {len(self.current_search)}"

        self.setUpdatesEnabled(True)
        return result_message


class SearchCriteria:
    def __init__(self, text, match_count, highlight, options):
        super().__init__()
        self.text = text
        self.match_count = match_count
        self.highlight = highlight
        self.options = options

    def __str__(self):
        return f"text={self.text}\tfind-item={self.match_count}\thighlight={self.highlight}"


class XMLSearch(QDockWidget):
    search_change_event = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        super().__init__()
        self.search_text = QLineEdit()
        self.btn_next = QPushButton("Next")
        self.highlight = QCheckBox("Highlight")
        self.match_case = QCheckBox("Match Case")
        self.match_option = QComboBox()
        self.match_count = 0
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Search")
        self.search_text.setPlaceholderText("Find in document")
        self.search_text.textChanged.connect(self.search_text_changed)
        self.btn_next.clicked.connect(self.next_button_press)
        self.highlight.stateChanged.connect(self.search_changed)
        self.match_case.stateChanged.connect(self.search_changed)
        self.match_option.currentTextChanged.connect(self.search_changed)
        self.match_option.setEditable(False)
        self.match_option.addItems(_SEARCH_CRITERIA.keys())
        self.match_option.setCurrentText("Contains")

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_text)
        search_layout.addWidget(self.btn_next)

        options_layout = QHBoxLayout()
        options_layout.addWidget(self.match_option)
        options_layout.addWidget(self.match_case)
        options_layout.addWidget(self.highlight)
        options_layout.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(options_layout)
        layout.addLayout(search_layout)

        container = QGroupBox()
        container.setLayout(layout)

        self.setWidget(container)

    def search_changed(self):
        # Set match options
        match_options = _SEARCH_CRITERIA[self.match_option.currentText()]
        if self.match_case.isChecked():
            match_options = match_options | Qt.MatchCaseSensitive
        # Always recursive and wrapped
        # TODO: Remove recirsive search
        match_options = match_options | Qt.MatchRecursive | Qt.MatchWrap

        search_criteria = SearchCriteria(
            text=self.search_text.text().strip(),
            match_count=self.match_count,
            highlight=self.highlight.isChecked(),
            options=match_options
        )
        if search_criteria.text != "":
            self.search_change_event.emit(search_criteria)

    def search_text_changed(self):
        self.match_count = 0
        self.search_changed()

    def next_button_press(self):
        # Find next match
        self.match_count += 1
        self.search_changed()



def main():
    app = QApplication(sys.argv)
    ex = XMLSearch()
    #ex.set_file("/mnt/Dev/test/nasa.xml")
    ex.show()
    sys.exit(app.exec_())

    # model = XMLViewModel()
    # model.set_xml_file("/mnt/Dev/test/nasa.xml")
    # model.reload()


if __name__ == '__main__':
    main()
