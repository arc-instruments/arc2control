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
        self.multiplierCombo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,\
            QtWidgets.QSizePolicy.Policy.Maximum)
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

    def setObjectName(self, what):
        super().setObjectName(what)
        self.baseValueSpinBox.setObjectName('%s_baseValue' % what)
        self.multiplierCombo.setObjectName('%s_multiplier' % what)

    def setDurations(self, durations):
        self.baseValueSpinBox.clear()
        self.multiplierCombo.clear()

        for (lbl, mult) in durations:
            self.multiplierCombo.addItem(lbl, mult)

    def setCurrentMultiplierIndex(self, idx):
        self.multiplierCombo.setCurrentIndex(idx)

    def setCurrentMultiplier(self, mlt):
        if isinstance(mlt, str):
            check_labels = True
        elif isinstance(mlt, (int, float)):
            check_labels = False
        else:
            raise ValueError("Invalid multiplier; it must be a string or number")

        for i in range (0, self.multiplierCombo.count()):
            label = self.multiplierCombo.itemText(i)
            mult = self.multiplierCombo.itemData(i)

            if check_labels:
                if label == mlt:
                    self.multiplierCombo.setCurrentIndex(i)
                    return
            else:
                if mult == mlt:
                    self.multiplierCombo.setCurrentIndex(i)
                    return

        raise ValueError("Multiplier doesn't exist in widget")

    def getDuration(self):
        base = self.baseValueSpinBox.value()
        multiplier = self.multiplierCombo.currentData()

        return base * multiplier

    def setDuration(self, value, mult):
        self.baseValueSpinBox.setValue(value)
        self.setCurrentMultiplier(mult)
