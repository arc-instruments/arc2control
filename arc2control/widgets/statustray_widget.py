from PyQt6 import QtCore, QtWidgets, QtGui


class StatusTrayWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.icons = {}

    def addStatusIcon(self, key, pixmap, tooltip=None):
        if key in self.icons:
            return
        label = QtWidgets.QLabel()
        label.setPixmap(pixmap)
        if tooltip:
            label.setToolTip(tooltip)
        self.icons[key] = label
        self.layout().addWidget(label)

    def removeStatusIcon(self, key):
        if key not in self.icons:
            return
        label = self.icons.pop(key)
        self.layout().removeWidget(label)
        label.setParent(None)
        del label
