import html
from enum import Enum

from PyQt5.QtCore import QRectF, QSizeF, QVariant, Qt
from PyQt5.QtGui import QTextDocument, QStandardItem, QIcon
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem

from app import AppSettings


class ItemType(Enum):
    NODE = 1,
    DICT = 2,
    LIST = 3


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
        if not doc:
            painter.restore()
            super().paint(painter, option, index)
        else:
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
        htm = index.model().data(index, Qt.UserRole)
        if htm and not isinstance(htm, QVariant):
            doc = QTextDocument()
            doc.setDefaultFont(self.font)
            doc.setHtml(htm)
            return doc


class XMLDataItem(QStandardItem):
    __ROOT_ICON = QIcon.fromTheme("folder")
    __NODE_ICON = QIcon.fromTheme("text-x-generic")
    __LIST_ICON = QIcon.fromTheme("x-office-spreadsheet")

    __TEXT_NODE = "#text"

    def __init__(self, name, data, parent_sub_index=None, column_name=None):
        super().__init__()
        self.colors = AppSettings.color_theme()
        self.name = self._clean_text(name)
        self.parent_sub_index = parent_sub_index
        self.column_name = column_name
        self.attributes = {}
        self.datadict = {}
        self.datalist = []
        # The basic node name
        self.datatext = None
        # The HTML formatted name
        self.htmltext = None
        # The plain text name to display
        self.plaintext = None

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
        elif data is None:
            self.datatext = ""
            self.nodetype = ItemType.NODE
        else:
            print(f"{str(data)} has an unexpected type ")
        self._create_display_texts()

    def can_tabulate(self):
        return self.nodetype == ItemType.LIST

    def data(self, role: int = None):
        match role:
            case Qt.DisplayRole:
                return self.plaintext
            case Qt.UserRole:
                return self.htmltext
            case _:
                return QVariant()

    def _create_display_texts(self):
        """
        Creates display texts for this node.
        - If the node is a dictionary (has children) - Show node name only with +/- button
        - If the node is a list of items - Show count and table options
        - Otherwise, simply show as key = value format
        :return: returns nothing, sets the HTML and PlainText of the parent
        """
        match self.nodetype:
            case ItemType.DICT:
                if self.name == "":
                    self.plaintext = "..."
                    self.htmltext = f"<p><span style='color:{self.colors['node']};'>{self.plaintext}</span></p>"
                else:
                    # It's a root
                    self.plaintext = self.name
                    self.htmltext = f"<p><span style='color:{self.colors['node']};'>{self.name}</span></p>"
                    self.setIcon(self.__ROOT_ICON)

            case ItemType.LIST:
                # It's a list
                self.plaintext = f"{self.name} (list of {len(self.datalist)} elements)"
                self.htmltext = f"<p>" \
                                f"  <span style='color:{self.colors['node']};'>{self.name}</span>" \
                                f"  <span style='color:{self.colors['comment']};'>" \
                                f"      <em>...list with {len(self.datalist)} item(s)</em>" \
                                f"  </span>" \
                                f"</p>"
                self.setIcon(self.__LIST_ICON)

            case _:
                if self.name == "":
                    self.plaintext = self.datatext
                    # self.colors['value']
                    self.htmltext = f"<p>" \
                                    f"<span style='color:{self.colors['value']};'>{self.datatext}</span>" \
                                    f"</p>"
                else:
                    self.plaintext = f"{self.name} = {self.datatext}"
                    self.htmltext = f"<p>" \
                                    f"<span style='color:{self.colors['key']};'>{self.name}</span>" \
                                    f" = " \
                                    f"<span style='color:{self.colors['value']};'>{self.datatext}</span>" \
                                    f"</p>"
                    self.setIcon(self.__NODE_ICON)

        self.setText(self.plaintext)

        if AppSettings.show_attributes() and len(self.attributes) > 0:
            attr_text, attr_html = self._format_attributes()
            self.plaintext = self.plaintext.replace("</p>", f"  {attr_text}</p>")
            self.htmltext = self.htmltext.replace("</p>", f"  {attr_html}</p>")

        self.htmltext = self.htmltext.replace('\n', "<br/>")

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