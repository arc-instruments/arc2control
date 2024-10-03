from collections.abc import Iterable
from PyQt6.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex
from PyQt6.QtWidgets import QTableView, QAbstractItemView


class DatasetTableView(QTableView):

    def __init__(self, dataset, formatter=None, heads=None, parent=None):
        super(DatasetTableView, self).__init__(parent=parent)
        self.setSelectionBehavior(\
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(18)
        self._model = DatasetTableModel(dataset, formatter, heads)
        self.setModel(self._model)

    def setDataset(self, dataset, formatter=None, heads=None):
        self._model.setDataset(dataset, formatter, heads)


class DatasetTableModel(QAbstractTableModel):

    def __init__(self, dataset, formatter=None, heads=None, parent=None):
        super(DatasetTableModel, self).__init__(parent=parent)
        self.setDataset(dataset, formatter, heads)

    @property
    def _structured(self):
        d = self._dataset
        return (d.dtype.names is not None) and (d.dtype.fields is not None)

    def setDataset(self, dataset, formatter=None, heads=None):
        self._dataset = dataset

        if self._structured:
            nCols = len(self._dataset.dtype.fields)
            self._heads = list(self._dataset.dtype.names)
        else:
            if len(self._dataset.shape) > 2:
                raise ValueError("Only 2D arrays are supported")
            try:
                nCols = self._dataset.shape[1]
            except IndexError: # shape is probably "(X, )" or "(X)"
                nCols = 1
            self._heads = ["%d" % c for c in range(nCols)]

        # override headings if required
        if heads is not None:
            if len(heads) != nCols:
                raise ValueError("Length of headings does not match columns")
            else:
                self._heads = heads

        if formatter is None:
            self._formatter = ["%e"] * nCols
            return

        if isinstance(formatter, str):
            self._formatter = [formatter] * nCols
        elif isinstance(formatter, Iterable):
            if len(formatter) != nCols:
                raise ValueError("Length of formatter does not match columns")
            else:
                self._formatter = formatter
        else:
            raise ValueError("Wrong formatter type")

    def rowCount(self, parent=QModelIndex()):
        return self._dataset.shape[0]

    def columnCount(self, parent=QModelIndex()):
        return len(self._heads)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()

            # either structured or shape is "(X, Y)"
            if self._structured or len(self._dataset.shape) > 1:
                return self._formatter[col] % self._dataset[row][col]
            else: # just a vector; shape is "(X, )" or "(X)"
                return self._formatter[col] % self._dataset[row]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return QVariant()

    def flags(self, _index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if role != Qt.ItemDataRole.DisplayRole:
            return QVariant()
        if orientation == Qt.Orientation.Horizontal:
            return self._heads[section]
        else:
            return "%d" % section