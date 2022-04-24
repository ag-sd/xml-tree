import datetime
import html
import json
import os
import sys
from enum import Enum

import xmltodict
from PyQt5.QtCore import Qt, pyqtSignal, QItemSelectionModel, QModelIndex, QRectF, QSize, QSizeF
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon, QTextDocument
from PyQt5.QtWidgets import QTreeView, QAbstractItemView, \
    QApplication, QStyledItemDelegate, QStyleOptionViewItem, QStyle
from lxml import etree

import app
from app import AppSettings


class ItemType(Enum):
    NODE = 1,
    DICT = 2,
    LIST = 3


class XMLDictStandardItem(QStandardItem):
    __ROOT_ICON = QIcon.fromTheme("folder")
    __NODE_ICON = QIcon.fromTheme("text-x-generic")
    __LIST_ICON = QIcon.fromTheme("x-office-spreadsheet")

    __TEXT_NODE = "#text"

    def __init__(self, name, data):
        super().__init__()
        self.colors = AppSettings.color_theme()
        self.name = self._clean_text(name)
        self.attributes = {}
        self.datadict = {}
        self.datalist = []
        self.datatext = None
        self.htmltext = None

        if isinstance(data, dict):
            self.attributes, self.datadict = self._extract_attrs(data)
            # there can be only attributes in the dict
            if len(self.datadict) == 1 and self.__TEXT_NODE in self.datadict:
                self.datatext = self.datadict[self.__TEXT_NODE]
                self.datadict.pop(self.__TEXT_NODE)
                self.nodetype = ItemType.NODE
            else:
                self.nodetype = ItemType.DICT
        elif isinstance(data, list):
            self.datalist = data
            self.nodetype = ItemType.LIST
        elif isinstance(data, str):
            self.datatext = self._clean_text(data)
            self.nodetype = ItemType.NODE
        else:
            raise TypeError(f"data has an unexpected type of {type(data)}")
        self._create_display_texts()

    def _create_display_texts(self):
        if self.nodetype == ItemType.DICT:
            # It's a root
            self.setIcon(self.__ROOT_ICON)
            plaintext = self.name
            self.htmltext = f"<p><span style='color:{self.colors['node']};'>{self.name}</span></p>"
        elif self.nodetype == ItemType.LIST:
            # It's a list
            self.setIcon(self.__LIST_ICON)
            plaintext = f"{self.name} (list of {len(self.datalist)} elements)"
            self.htmltext = f"<p>" \
                            f"  <span style='color:{self.colors['node']};'>{self.name}</span>" \
                            f"  <span style='color:{self.colors['comment']};'>" \
                            f"      <em>...list with {len(self.datalist)} item(s)</em>" \
                            f"  </span>" \
                            f"</p>"
        else:
            self.setIcon(self.__NODE_ICON)
            plaintext = f"{self.name} = {self.datatext}"
            self.htmltext = f"<p>" \
                            f"<span style='color:{self.colors['key']};'>{self.name}</span>" \
                            f" = " \
                            f"<span style='color:{self.colors['value']};'>{self.datatext}</span>" \
                            f"</p>"

        if AppSettings.show_attributes() and len(self.attributes) > 0:
            attr_text, attr_html = self._format_attributes()
            plaintext = plaintext.replace("</p>", f"  {attr_text}</p>")
            self.htmltext = self.htmltext.replace("</p>", f"  {attr_html}</p>")

        self.htmltext = self.htmltext.replace('\n', "<br/>")
        self.setText(plaintext)
            
    def _format_attributes(self):
        """
        Pretty prints attributes and returns a list of these in plaintext and html formats
        :return: 
        """
        _text = "[ "
        _html = "[ "

        for key in self.attributes:
            _text = _text + f"{self._clean_text(key)}=\"{self._clean_text(self.attributes[key])}\""
            _html = _html + f"<i>{key} = " \
                            f"<span style='color:{self.colors['attribute']};'>" \
                            f"\"{self.attributes[key]}\"</span></i> "
        return _text + " ]", _html + " ]"

    @staticmethod
    def _clean_text(text):
        """
        Cleans the input data and html escapes it
        :param text: 
        :return: 
        """
        if text is None:
            return None
        text = html.escape(text)
        return text.strip()

    @staticmethod
    def _extract_attrs(datadict):
        """
        Extracts the attributes from the datadict and returns a dictionary of attributes and the updated datadict
        :param datadict:
        :return:
        """

        attributes = {}
        # Collect attributes
        for key in datadict:
            if key.startswith("@"):
                attributes[key[1:]] = datadict[key]

        # Remove attributes from data dict
        for key in attributes:
            datadict.pop(f"@{key}")

        return attributes, datadict


class XMLItemDelegate(QStyledItemDelegate):
    # https://www.qtcentre.org/threads/22863-HTML-and-QStandardItem
    # https://www.qtcentre.org/threads/5548-QStandardItem-subpart-of-the-text-as-bold
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.font = AppSettings.font()

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem()
        options.__init__(option)
        self.initStyleOption(options, index)
        options.textElideMode = Qt.ElideRight

        painter.save()

        doc = self._get_document(index)

        # get focus rect and selection background
        options.text = ""
        options.widget.style().drawControl(QStyle.CE_ItemViewItem, options, painter)

        # draw using our rich text document
        if options.features & QStyleOptionViewItem.HasDecoration != QStyleOptionViewItem.HasDecoration:
            # This item has no decorations
            painter.translate(options.rect.left(), options.rect.top())
        else:
            painter.translate(options.rect.left() + option.decorationSize.width(), options.rect.top())
        rect = QRectF(0, 0, options.rect.width(), options.rect.height())
        # rect.__init__(0, 0, options.rect.width(), options.rect.height())
        doc.drawContents(painter, rect)

        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem()
        options.__init__(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        doc.setDefaultFont(self.font)
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        size = QSizeF(doc.idealWidth(), doc.size().height())
        return size.toSize()

    def _get_document(self, index):
        item = self.parent.model.itemFromIndex(index)
        doc = QTextDocument()
        doc.setDefaultFont(self.font)
        doc.setHtml(item.htmltext)
        return doc


class XMLViewModel(QStandardItemModel):

    load_event = pyqtSignal(str)

    def __init__(self, xml_file=None):
        super().__init__()
        self.data_file = xml_file

        if xml_file:
            self.reload()

    def set_xml_file(self, xml_file):
        self.data_file = xml_file

    def reload(self):
        start_time = datetime.datetime.now()
        data_dict = {}
        parser = None
        if not self.data_file:
            return
        # TODO CLean this code up
        # try:
        app.logger.debug("Starting load")
        _, ext = os.path.splitext(self.data_file)

        if ext.upper().startswith(".HTM"):
            app.logger.debug("This is an HTML file")
            parser = etree.HTMLParser()
        elif ext.upper() == ".XML":
            app.logger.debug("This is an XML file")
            parser = etree.XMLParser()
        elif ext.upper() == ".JSON":
            app. logger.debug("This is a JSON file")
            with open(self.data_file, "r") as f:
                data_dict = json.load(f)
            parser = None
        else:
            app.logger.debug("This is an Unsupported file. It cannot be loaded")
            raise Exception("This is an unsupported file. Only HTML, XML and JSON files permitted")

        if parser:
            app.logger.debug("in If parser")
            xml = etree.parse(self.data_file, parser=parser).getroot()
            data_dict = xmltodict.parse(etree.tostring(xml))

        parse_end_time = datetime.datetime.now() - start_time
        app.logger.debug("Parsed XML, building tree")
        # except Exception as e:
        #     message = f"Error while loading file {str(e)}"
        #     self.load_event.emit(message)
        #     app.logger.error(message)
        #     return

        self.clear()
        items = []
        for key in data_dict:
            items.append(XMLDictStandardItem(key, data_dict[key]))
        self.invisibleRootItem().appendRows(items)
        app.logger.debug("Tree built")
        total_time = datetime.datetime.now() - start_time
        log = f"File Loaded in {total_time.total_seconds()} seconds. " \
              f"(Took {parse_end_time.total_seconds()} seconds to parse)"
        app.logger.debug(log)

        self.load_event.emit(log)

    def canFetchMore(self, parent: QModelIndex):
        item = self.itemFromIndex(parent)
        if item is not None:
            # If it already has children or does not have children at all, return false
            return not (item.hasChildren() or (len(item.datadict) == 0 and len(item.datalist) == 0))
        else:
            return super().rowCount(parent)

    def fetchMore(self, parent: QModelIndex):
        item = self.itemFromIndex(parent)
        if item is not None:
            rows = []
            if item.nodetype == ItemType.DICT:
                for child in item.datadict:
                    rows.append(XMLDictStandardItem(child, item.datadict[child]))
            elif item.nodetype == ItemType.LIST:
                for index, element in enumerate(item.datalist):
                    rows.append(XMLDictStandardItem(item.name, element))
            else:
                app.logger.warn("This case shouldnt occur! Test expansion functions!!")
            app.logger.debug(f"Adding {len(rows)} child(ren) to {item.text()}")
            self.beginInsertRows(parent, 0, len(rows))
            item.insertRows(0, rows)
            self.endInsertRows()
        else:
            super().fetchMore(parent)

    def hasChildren(self, parent):
        item = self.itemFromIndex(parent)
        if item is not None:
            return item.hasChildren() or len(item.datadict) > 0 or len(item.datalist) > 0
        else:
            return super().rowCount(parent)

    def rowCount(self, parent):
        item = self.itemFromIndex(parent)
        if item is not None:
            if item.hasChildren():
                return item.rowCount()
            else:
                app.logger.debug(f"Visit node for the first time")
                return 0
        else:
            return super().rowCount(parent)


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
            self.model.load_event.connect(self.model_xml_load_event)
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
        app.logger.error("unimplemented!")
        pass
    #     item = self.model.itemFromIndex(current)
    #     if item is not None:
    #         self.model.get_xpath(item.node)
    #         self.path_changed_event.emit(self.model.get_xpath(item.node))

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


if __name__ == '__main__':
    appl = QApplication(sys.argv)
    _ = XMLTreeView()
    _.show()
    _.setMinimumSize(500, 800)
    # _.set_file("/mnt/Dev/test/REC-xml-20081126.xml")
    _.set_file("/mnt/Dev/test/part.XML")
    # _.set_file("/mnt/Dev/test/nasa.xml")
    sys.exit(appl.exec_())
