from PyQt6 import QtCore, QtWidgets, QtGui


class DurationWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.baseValueSpinBox = QtWidgets.QSpinBox()
        self.baseValueSpinBox.setMaximum(1000)
        self.baseValueSpinBox.setMinimum(0)
        self.baseValueSpinBox.setValue(100)
        self.baseValueSpinBox.setMinimumWidth(40)

        self.multiplierCombo = QtWidgets.QComboBox()
        self.multiplierCombo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,\
            QtWidgets.QSizePolicy.Policy.Preferred)
        self.multiplierCombo.addItem('ns', 1.0e-9)
        self.multiplierCombo.addItem('μs', 1.0e-6)
        self.multiplierCombo.addItem('ms', 1.0e-3)
        self.multiplierCombo.addItem('s', 1.0)
        self.multiplierCombo.setMinimumWidth(40)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStretch(1, 0)
        layout.addWidget(self.baseValueSpinBox)
        layout.addWidget(self.multiplierCombo)

    def getDuration(self):
        base = self.baseValueSpinBox.value()
        multiplier = self.multiplierCombo.currentData()

        return base * multiplier
