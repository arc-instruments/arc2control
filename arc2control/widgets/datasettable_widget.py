from collections.abc import Iterable
from PyQt6.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex


class StructuredTableModel(QAbstractTableModel):

    def __init__(self, dataset, formatter=None, parent=None):
        super(StructuredTableModel, self).__init__(parent=parent)
        self.setDataset(dataset, formatter)

    def setDataset(self, dataset, formatter=None):
        self._dataset = dataset
        self._heads = []
        nCols = len(self._dataset.dtype.fields)
        for item in self._dataset.dtype.fields.keys():
            self._heads.append(item)

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
        return len(self._dataset.dtype.fields)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()

            return self._formatter[col] % self._dataset[row][col]

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