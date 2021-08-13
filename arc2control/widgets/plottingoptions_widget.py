from PyQt6 import QtCore, QtWidgets
from .generated.plottingoptions import Ui_PlottingOptionsWidget

from enum import Enum


class DisplayType(Enum):
    Resistance = 0b1
    Current = 0b10
    AbsCurrent = 0b100
    Conductance = 0b1000

    def plotLabel(self):
        if self == DisplayType.Resistance:
            return {'text': 'Resistance', 'units': 'Ω'}
        elif self == DisplayType.Current:
            return {'text': 'Current', 'units': 'A'}
        elif self == DisplayType.AbsCurrent:
            return {'text': 'Abs. Current', 'units': 'A'}
        elif self == DisplayType.Conductance:
            return {'text': 'Conductance', 'units': 'S'}
        else:
            return None


class YScale(Enum):
    Linear = 0b1
    Log = 0b10


class PlottingOptionsWidget(Ui_PlottingOptionsWidget, QtWidgets.QWidget):

    displayTypeChanged = QtCore.pyqtSignal(DisplayType)
    xRangeChanged = QtCore.pyqtSignal(int)
    yScaleChanged = QtCore.pyqtSignal(YScale)

    def __init__(self, parent=None):
        Ui_PlottingOptionsWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.setupUi(self)

        self.displayTypeComboBox.addItem(" R : Resistance", DisplayType.Resistance)
        self.displayTypeComboBox.addItem(" I : Current", DisplayType.Current)
        self.displayTypeComboBox.addItem("|I|: Absolute Current", DisplayType.AbsCurrent)
        self.displayTypeComboBox.addItem(" G : Conductance", DisplayType.Conductance)
        self.displayTypeComboBox.currentIndexChanged.connect(self.__displayIndexChanged)
        self.rangePointsSpinBox.valueChanged.connect(self.__rangePointsValueChanged)
        self.limitedRangeRadioButton.toggled.connect(self.__xRangeRadioChecked)
        self.fullRangeRadioButton.toggled.connect(self.__xRangeRadioChecked)
        self.linearScaleRadio.toggled.connect(self.__scaleRadioChecked)
        self.logScaleRadio.toggled.connect(self.__scaleRadioChecked)

    def __displayIndexChanged(self, idx):
        data = self.displayTypeComboBox.itemData(idx)
        self.logScaleRadio.setEnabled(data != DisplayType.Current)

        self.displayTypeChanged.emit(data)

    def __scaleRadioChecked(self, *args):
        if self.linearScaleRadio.isChecked():
            self.yScaleChanged.emit(YScale.Linear)
            self.__enableDisplayType(DisplayType.Current, True)
        else:
            self.yScaleChanged.emit(YScale.Log)
            self.__enableDisplayType(DisplayType.Current, False)

    def __xRangeRadioChecked(self, *args):
        if self.fullRangeRadioButton.isChecked():
            self.rangePointsSpinBox.setEnabled(False)
            self.xRangeChanged.emit(None)
        else:
            self.rangePointsSpinBox.setEnabled(True)
            self.xRangeChanged.emit(self.rangePointsSpinBox.value())

    def __rangePointsValueChanged(self, value):
        self.xRangeChanged.emit(value)

    def __enableDisplayType(self, typ, enable):
        model = self.displayTypeComboBox.model()
        for i in range(self.displayTypeComboBox.count()):
            itemData = self.displayTypeComboBox.itemData(i)
            if itemData == typ:
                item = model.item(i)
                if enable:
                    item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEnabled)
                else:
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEnabled)
                break

    @property
    def xRange(self):
        if self.limitedRangeRadioButton.isChecked():
            return self.rangePointsSpinBox.value()
        else:
            return None

    @property
    def yScale(self):
        if self.linearScaleRadio.isChecked():
            return YScale.Linear
        else:
            return YScale.Log

    @property
    def displayType(self):
        return self.displayTypeComboBox.currentData()
