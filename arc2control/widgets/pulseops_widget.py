from PyQt6 import QtCore, QtWidgets
from . import GeneratedElements
from .common import Polarity


class PulseOpsWidget(GeneratedElements.Ui_PulseOpsWidget, QtWidgets.QWidget):

    #                                      voltage, pulse width
    positivePulseClicked = QtCore.pyqtSignal(float, float)
    negativePulseClicked = QtCore.pyqtSignal(float, float)
    positivePulseReadClicked = QtCore.pyqtSignal(float, float)
    negativePulseReadClicked = QtCore.pyqtSignal(float, float)

    def __init__(self, parent=None):
        GeneratedElements.Ui_PulseOpsWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setupUi(self)

        self.lockPulseCheckBox.stateChanged.connect(\
            self.__lockPulseCheckBoxChecked)
        self.posPulseButton.clicked.connect(self.__positivePulseClickedFn)
        self.negPulseButton.clicked.connect(self.__negativePulseClickedFn)
        self.posPulseReadButton.clicked.connect(self.__positivePulseReadClickedFn)
        self.negPulseReadButton.clicked.connect(self.__negativePulseReadClickedFn)

        self.positivePulseSpinBox.valueChanged.connect(self.__onPositivePulseChanged)
        self.positiveDurationWidget.durationChanged.connect(self.__onPositivePulseChanged)

    def positiveParams(self):
        return self.__pulseParams(Polarity.POSITIVE)

    def negativeParams(self):
        return self.__pulseParams(Polarity.NEGATIVE)

    def __pulseParams(self, polarity):
        if self.lockPulseCheckBox.isChecked():
            vbox = self.positivePulseSpinBox
            pbox = self.positiveDurationWidget
        else:
            if polarity == Polarity.POSITIVE:
                vbox = self.positivePulseSpinBox
                pbox = self.positiveDurationWidget
            elif polarity == Polarity.NEGATIVE:
                vbox = self.negativePulseSpinBox
                pbox = self.negativeDurationWidget
            else:
                raise Exception("Unknown polarity?")

        voltage = polarity.multiplier() * vbox.value()
        pulsewidth = pbox.getDuration()

        return (voltage, pulsewidth)

    def pulsesLocked(self):
        return self.lockPulseCheckBox.isChecked()

    def setPulseEnabled(self, polarity, enabled):
        if polarity == Polarity.POSITIVE:
            self.posPulseButton.setEnabled(enabled)
        elif polarity == Polarity.NEGATIVE:
            self.negPulseButton.setEnabled(enabled)
        else:
            raise Exception("Unknown polarity?")

    def setPulseReadEnabled(self, polarity, enabled):
        if polarity == Polarity.POSITIVE:
            self.posPulseReadButton.setEnabled(enabled)
        elif polarity == Polarity.NEGATIVE:
            self.negPulseReadButton.setEnabled(enabled)
        else:
            raise Exception("Unknown polarity?")

    def __onPositivePulseChanged(self, *args):
        if not self.pulsesLocked():
            return

        self.negativePulseSpinBox.setValue(self.positivePulseSpinBox.value())
        base = self.positiveDurationWidget.getBaseValue()
        mult = self.positiveDurationWidget.getMultiplier()
        self.negativeDurationWidget.setDuration(base, mult)

    def __positivePulseClickedFn(self):
        (v, pw) = self.__pulseParams(Polarity.POSITIVE)
        self.positivePulseClicked.emit(v, pw)

    def __negativePulseClickedFn(self):
        (v, pw) = self.__pulseParams(Polarity.NEGATIVE)
        self.negativePulseClicked.emit(v, pw)

    def __positivePulseReadClickedFn(self):
        (v, pw) = self.__pulseParams(Polarity.POSITIVE)
        self.positivePulseReadClicked.emit(v, pw)

    def __negativePulseReadClickedFn(self):
        (v, pw) = self.__pulseParams(Polarity.NEGATIVE)
        self.negativePulseReadClicked.emit(v, pw)

    def __lockPulseCheckBoxChecked(self, locked):
        self.negativeDurationWidget.setEnabled(not locked)
        self.negativePulseSpinBox.setEnabled(not locked)
        if locked:
            self.__onPositivePulseChanged()
