from PyQt6 import QtCore, QtWidgets
from .generated.readops import Ui_ReadOpsWidget
import numpy as np
from pyqtgraph import siFormat


class ReadOpsWidget(Ui_ReadOpsWidget, QtWidgets.QWidget):

    readoutVoltageChanged = QtCore.pyqtSignal(float)
    readSelectedClicked = QtCore.pyqtSignal()
    readAllClicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        Ui_ReadOpsWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setupUi(self)

        self.readoutVoltageSpinBox.valueChanged.connect(\
            self.readoutVoltageChanged.emit)
        self.readSelectedButton.clicked.connect(\
            self.readSelectedClicked.emit)
        self.readAllButton.clicked.connect(\
            self.readAllClicked.emit)

    def readoutVoltage(self):
        return self.readoutVoltageSpinBox.value()

    def setValue(self, w, b, value, suffix='Ω'):
        if np.isnan(value):
            actual_value = "N/A"
        else:
            actual_value = siFormat(value, suffix=suffix)

        self.selectedLabel.setText(\
            "W = %d | B = %d – %s" % (w+1, b+1, actual_value))

    def setReadAllEnabled(self, enabled):
        self.readAllButton.setEnabled(enabled)

    def setReadSelectedEnabled(self, enabled):
        self.readSelectedButton.setEnabled(enabled)
