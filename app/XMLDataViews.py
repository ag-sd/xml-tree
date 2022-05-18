import datetime
import json
import os
import sys
from builtins import super
from collections import OrderedDict

import xmltodict
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal, QItemSelectionModel, QModelIndex, QAbstractTableModel, QVariant
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import QTreeView, QAbstractItemView, \
    QApplication, QDockWidget, QHBoxLayout, QGroupBox, QTableView
from lxml import etree
from ordered_set import OrderedSet

import app
from app import AppSettings
from app.XMLCommon import XMLDataItem, ItemType, XMLItemDelegate


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
        """
        Rebuilds this model very lazily
        :return: returns nothing.
        """

        def parse(file, parser):
            xml = etree.parse(file, parser=parser).getroot()
            return xmltodict.parse(etree.tostring(xml))

        def build_tree(tree, datadict):
            tree.clear()
            items = []
            for key in datadict:
                items.append(XMLDataItem(key, datadict[key]))
            tree.invisibleRootItem().appendRows(items)

        # Basic defences if file does not exist
        if not self.data_file:
            app.logger.warn("File not provided, unable to load anything")
            return
        elif not os.path.exists(self.data_file):
            app.logger.warn(f"File {self.data_file} does not exist!")
            return

        try:
            start_time = datetime.datetime.now()
            app.logger.debug("Starting load")
            _, ext = os.path.splitext(self.data_file)

            # check the file type
            if ext.upper().startswith(".HTM"):
                app.logger.debug("This is an HTML file")
                data_dict = parse(self.data_file, etree.HTMLParser())
            elif ext.upper() == ".JSON":
                app.logger.debug("This is a JSON file")
                with open(self.data_file, "r") as f:
                    data_dict = json.load(f)
            elif ext.upper() == ".XML":
                app.logger.debug("This is an XML file")
                data_dict = parse(self.data_file, etree.XMLParser())
            else:
                app.logger.debug("This is an Unsupported file. It cannot be loaded")
                raise Exception("This is an unsupported file. Only HTML, XML and JSON files permitted")

            parse_end_time = datetime.datetime.now() - start_time
            app.logger.debug("Parsed XML, building tree")
            # Attempt to build the tree
            build_tree(self, data_dict)
            total_time = datetime.datetime.now() - start_time
            log = f"File Loaded in {total_time.total_seconds()} seconds. " \
                  f"(Took {parse_end_time.total_seconds()} seconds to parse)"
            # Return with metrics
            self.load_event.emit(log)

        except Exception as e:
            message = f"Error while loading file {str(e)}"
            app.logger.exception(message)
            self.load_event.emit(message)

    def canFetchMore(self, index: QModelIndex):
        """
        Returns true if the item referenced by the index has children, but hasn't been built
        :param index:
        :return: If item already has children or does not have children at all, return false
        """
        item = self.itemFromIndex(index)
        if item is not None:
            # If it already has children or does not have children at all, return false
            return not (item.hasChildren() or (len(item.datadict) == 0 and len(item.datalist) == 0))
        else:
            return super().rowCount(index)

    def fetchMore(self, parent: QModelIndex):
        """
        Returns all children of the parent
        :param parent:
        :return: returns nothing. Inserts all child-nodes under the parent
        """
        item = self.itemFromIndex(parent)
        if item is not None:
            rows = []
            if item.nodetype == ItemType.DICT:
                for child in item.datadict:
                    rows.append(XMLDataItem(child, item.datadict[child]))
            elif item.nodetype == ItemType.LIST:
                for index, element in enumerate(item.datalist):
                    rows.append(XMLDataItem(item.name, element))
            else:
                app.logger.warn("This case shouldnt occur! Test expansion functions!!")
            app.logger.debug(f"Adding {len(rows)} child(ren) to {item.text()}")
            self.beginInsertRows(parent, 0, len(rows))
            item.insertRows(0, rows)
            self.endInsertRows()
        else:
            super().fetchMore(parent)

    def hasChildren(self, parent):
        """
        Checks if the parent is already built or can be built
        :param parent:
        :return: True if the parent has children or can have children
        """
        item = self.itemFromIndex(parent)
        if item is not None:
            return item.hasChildren() or len(item.datadict) > 0 or len(item.datalist) > 0
        else:
            return super().rowCount(parent)

    def rowCount(self, parent):
        """
        Returns the row count.
        :param parent:
        :return: If the parent has been built, return true row count, otherwise return 0
        """
        item = self.itemFromIndex(parent)
        if item is not None:
            if item.hasChildren():
                return item.rowCount()
            else:
                app.logger.debug(f"Visit node for the first time")
                return 0
        else:
            return super().rowCount(parent)

    @staticmethod
    def get_models_sorted_by_ancestry(model_indices):
        """
        Sorts the indices so that they can be deleted sequentially without changing the reference to anoter index
        in the lust. Sorts from child with least ancestors to the most
        :param model_indices:
        :return:
        """
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


class XMLTableViewModel(QAbstractTableModel):

    def __init__(self, tabledata):
        super().__init__()
        self._tabledata = tabledata
        self._cols = self._get_columns(tabledata)
        self._cache = {}

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self._tabledata)

    def columnCount(self, parent: QModelIndex = None) -> int:
        return len(self._cols)

    def data(self, index: QModelIndex, role: int = None):
        item = self.item(index)
        if item is None or isinstance(item, QVariant):
            return QVariant()
        return item.data(role)

    def item(self, index: QtCore.QModelIndex):
        if not index.isValid():
            return QVariant()

        p_index = QtCore.QPersistentModelIndex(index)
        item = self._cache.get(p_index)
        if item is None:
            row = self._tabledata[index.row()]
            col = self._cols[index.column()]
            if col in row:
                item = XMLDataItem("", row[col], parent_sub_index=index.row(), column_name=col)
                self._cache[p_index] = item
        return item

    def headerData(self, p_int, orientation, role=None):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._cols[p_int]
            elif orientation == Qt.Vertical:
                return p_int

    @staticmethod
    def _get_columns(tabledata):
        cols = OrderedSet()
        for item in tabledata:
            cols.update(item.keys())
        return list(cols)


class XMLTableView(QTableView):

    item_doubleclicked = pyqtSignal(QModelIndex, int, str)

    def __init__(self, parent, parent_index=None, tabledata=None):
        super().__init__(parent)
        self.tabledata = None
        self.parent_index = None
        self.datamodel = None
        if tabledata is not None and parent_index is not None:
            self.set_data(parent_index, tabledata)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.verticalHeader().setDefaultSectionSize(self.verticalHeader().fontMetrics().height() + 3)
        self.verticalHeader().hide()
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().setSectionsClickable(True)
        self.setSortingEnabled(True)
        self.setItemDelegate(XMLItemDelegate())
        self.doubleClicked.connect(self.item_double_click)

    def set_data(self, parent_index, tabledata):
        self.tabledata = tabledata
        self.parent_index = parent_index
        self.datamodel = XMLTableViewModel(tabledata)
        self.setModel(self.datamodel)

    def item_double_click(self, index):
        item = index.model().item(index)
        if item is not None:
            self.item_doubleclicked.emit(self.parent_index, item.parent_sub_index, item.column_name)



# Table Interaction -
# 1 Clicking a node in the table finds it in the tree
# 2 dbl click cell: If its a cell, show in tree, if its a dict: Expand in Tree


class PropertyPanel(QDockWidget):
    item_doubleclicked = pyqtSignal(QModelIndex, int, str)

    def __init__(self, parent):
        super(PropertyPanel, self).__init__(parent)
        self.table = XMLTableView(parent)
        self.table.item_doubleclicked.connect(self.model_dbl_click_event)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(self.table)

        container = QGroupBox()
        container.setLayout(layout)
        self.setWidget(container)

    def model_dbl_click_event(self, parent_index, parent_sub_index, coumn_name):
        self.item_doubleclicked.emit(parent_index, parent_sub_index, coumn_name)

    def tabulate(self, parent_index, data):
        self.table.set_data(parent_index, data)


class XMLTreeView(QTreeView):
    path_changed_event = pyqtSignal(str)
    xml_load_event = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.treemodel = XMLViewModel()
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

    def get_item(self, index):
        return self.treemodel.itemFromIndex(index)

    def show_node(self, index, sub_item_index=None, sub_item_field=None):
        self.scrollTo(index)
        item = self.get_item(index)
        # Build children if possible
        if self.model().hasChildren(index) and self.model().canFetchMore(index):
            self.model().fetchMore(index)
        # Jump to the index specified
        if self.model().hasChildren(index) and sub_item_index is not None:
            child = item.child(sub_item_index)
            if child is not None:
                self.selectionModel().select(child.index(), QItemSelectionModel.Select)
                self.scrollTo(child.index())





    def set_file(self, file):
        if os.path.exists(file) and os.path.isfile(file):
            app.logger.debug(f"Attempting to load {file}")
            self.treemodel = XMLViewModel(file)
            self.treemodel.load_event.connect(self.model_xml_load_event)
            self.setModel(self.treemodel)
            self.current_search.clear()
        else:
            app.logger.debug(f"{file} is not a valid path")

    def reload(self):
        self.treemodel.beginResetModel()
        self.treemodel.reload()
        self.treemodel.endResetModel()

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
        self.current_search = self.treemodel.findItems(criteria.text, criteria.options)
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
    # _ = XMLTreeView()
    # _.show()
    # _.setMinimumSize(500, 800)
    # # _.set_file("/mnt/Dev/test/REC-xml-20081126.xml")
    # # _.set_file("/mnt/Dev/test/part.XML")
    # # _.set_file("/mnt/Dev/test/nasa.xml")
    lis = [
        OrderedDict(
            [('P_PARTKEY', '1'), ('P_NAME', 'goldenrod lace spring peru powder'), ('P_MFGR', 'Manufacturer#1'),
             ('P_BRAND', 'Brand#13'), ('P_TYPE', 'PROMO BURNISHED COPPER'), ('P_SIZE', '7'),
             ('P_CONTAINER', 'JUMBO PKG'),
             ('P_RETAILPRICE', '901.00'), ('P_COMMENT', {"a": 1, "b": 2, "c": 3})]),
        OrderedDict(
            [('P_PARTKEY', '2'), ('P_NAME', 'blush rosy metallic lemon navajo'), ('P_MFGR', 'Manufacturer#1'),
             ('P_BRAND', 'Brand#13'), ('P_TYPE', 'LARGE BRUSHED BRASS'), ('P_SIZE', '1'), ('P_CONTAINER', 'LG CASE'),
             ('P_RETAILPRICE', '902.00'), ('P_COMMENT', [1, 2, 3, 4, 5])]),
        OrderedDict(
            [('P_PARTKEY', '3'), ('P_NAME', 'dark green antique puff wheat'), ('P_MFGR', 'Manufacturer#4'),
             ('P_BRAND', 'Brand#42'), ('P_TYPE', 'STANDARD POLISHED BRASS'), ('P_SIZE', '21'),
             ('P_CONTAINER', 'WRAP CASE'),
             ('P_RETAILPRICE', '903.00'), ('P_COMMENT', 'unusual excuses ac')]),
        OrderedDict(
            [('P_PARTKEY', '4'), ('P_NAME', 'chocolate metallic smoke ghost drab'), ('P_MFGR', 'Manufacturer#3'),
             ('P_BRAND', 'Brand#34'), ('P_TYPE', 'SMALL PLATED BRASS'), ('P_SIZE', '14'), ('P_CONTAINER', 'MED DRUM'),
             ('P_RETAILPRICE', '904.00'), ('P_COMMENT', 'ironi')]),
        OrderedDict(
            [('P_PARTKEY', '5'), ('P_NAME', 'forest blush chiffon thistle chocolate'), ('P_MFGR', 'Manufacturer#3'),
             ('P_BRAND', 'Brand#32'), ('P_TYPE', 'STANDARD POLISHED TIN'), ('P_SIZE', '15'), ('P_CONTAINER', 'SM PKG'),
             ('P_RETAILPRICE', '905.00'), ('P_COMMENT', 'pending, spe')]),
        OrderedDict(
            [('P_PARTKEY', '6'), ('P_NAME', 'white ivory azure firebrick black'), ('P_MFGR', 'Manufacturer#2'),
             ('P_BRAND', 'Brand#24'), ('P_TYPE', 'PROMO PLATED STEEL'), ('P_SIZE', '4'), ('P_CONTAINER', 'MED BAG'),
             ('P_RETAILPRICE', '906.00'), ('P_COMMENT', 'pending pinto be')]),
        OrderedDict(
            [('P_PARTKEY', '7'), ('P_NAME', 'blue blanched tan indian olive'), ('P_MFGR', 'Manufacturer#1'),
             ('P_BRAND', 'Brand#11'), ('P_TYPE', 'SMALL PLATED COPPER'), ('P_SIZE', '45'), ('P_CONTAINER', 'SM BAG'),
             ('P_RETAILPRICE', '907.00'), ('P_COMMENT', 'blithely ironic')]),
        OrderedDict(
            [('P_PARTKEY', '8'), ('P_NAME', 'ivory khaki cream midnight rosy'), ('P_MFGR', 'Manufacturer#4'),
             ('P_BRAND', 'Brand#44'), ('P_TYPE', 'PROMO BURNISHED TIN'), ('P_SIZE', '41'), ('P_CONTAINER', 'LG DRUM'),
             ('P_RETAILPRICE', '908.00'), ('P_COMMENT', 'furiously eve')]),
        OrderedDict(
            [('P_PARTKEY', '9'), ('P_NAME', 'thistle rose moccasin light floral'), ('P_MFGR', 'Manufacturer#4'),
             ('P_BRAND', 'Brand#43'), ('P_TYPE', 'SMALL BURNISHED STEEL'), ('P_SIZE', '12'),
             ('P_CONTAINER', 'WRAP CASE'),
             ('P_RETAILPRICE', '909.00'), ('P_COMMENT', 'thinly even request')])]
    _ = XMLTableView(None, lis)
    _.show()
    _.setMinimumSize(500, 800)
    sys.exit(appl.exec_())
