from PyQt6 import QtCore, QtWidgets
from .generated.rampops import Ui_RampOpsWidget


class RampOpsWidget(Ui_RampOpsWidget, QtWidgets.QWidget):

    rampSelectedClicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        Ui_RampOpsWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setupUi(self)

        self.rampSelectedButton.clicked.connect(\
            self.rampSelectedClicked.emit)

    def setRampEnabled(self, enabled):
        self.rampSelectedButton.setEnabled(enabled)

    def rampParams(self):
        vstart = self.rampVStartSpinBox.value()
        vstep = self.rampVStepSpinBox.value()
        vstop = self.rampVStopSpinBox.value()
        pulses = self.rampPulsesSpinBox.value()
        pw = self.rampPwDurationWidget.getDuration()
        inter = self.rampInterDurationWidget.getDuration()

        return (vstart, vstep, vstop, pw, inter, pulses)

    def showResultChecked(self):
        return self.showResultCheckBox.isChecked()
