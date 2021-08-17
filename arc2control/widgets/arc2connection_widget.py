import os.path
import sys
import time
from dataclasses import dataclass
from PyQt6 import QtCore, QtWidgets
from .generated.arc2connection import Ui_ArC2ConnectionWidget

from enum import Enum

from pyarc2 import Instrument, BiasOrder, ControlMode, ReadAt, \
    ReadAfter, DataMode, IdleMode

_CONNECTED_LABEL_STYLE = "QLabel { color: green; font-weight: bold }"
_DISCONNECTED_LABEL_STYLE = "QLabel { color: red; font-weight: bold }"


@dataclass
class ArC2Config:
    idleMode: IdleMode
    controlMode: ControlMode


class ArC2ConnectionWidget(Ui_ArC2ConnectionWidget, QtWidgets.QWidget):

    arc2ConfigChanged = QtCore.pyqtSignal(ArC2Config)
    connectionChanged = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        Ui_ArC2ConnectionWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setupUi(self)

        self.selectedFirmwareEdit.setText(os.path.realpath(
            os.path.join(os.path.dirname(sys.argv[0]), "efm03_20210628.bin")))

        self.internalControlRadio.toggled.connect(self.__controlModeChanged)
        self.headerControlRadio.toggled.connect(self.__controlModeChanged)
        self.floatDevsRadio.toggled.connect(self.__idleModeChanged)
        self.gndDevsRadio.toggled.connect(self.__idleModeChanged)
        self.selectFirmwareButton.clicked.connect(self.__openFirmware)
        self.connectArC2Button.clicked.connect(self.__arc2Connect)

        self._arc = None

    def __controlModeChanged(self, *args):

        if self._arc is None:
            return

        if self.internalControlRadio.isChecked():
            self._arc.set_control_mode(ControlMode.Internal).execute()
            self.arc2ConfigChanged.emit(self.arc2Config)
        if self.headerControlRadio.isChecked():
            self._arc.set_control_mode(ControlMode.Header).execute()
            self.arc2ConfigChanged.emit(self.arc2Config)

    def __idleModeChanged(self, *args):

        if self._arc is None:
            return

        if self.floatDevsRadio.isChecked():
            self._arc.ground_all_fast().float_all().execute()
            self.arc2ConfigChanged.emit(self.arc2Config)
        if self.gndDevsRadio.isChecked():
            self._arc.ground_all().execute()
            self.arc2ConfigChanged.emit(self.arc2Config)

    @property
    def controlMode(self):
        if self.internalControlRadio.isChecked():
            return ControlMode.Internal
        if self.headerControlRadio.isChecked():
            return ControlMode.Header

    @property
    def idleMode(self):
        if self.floatDevsRadio.isChecked():
            return IdleMode.Float
        if self.gndDevsRadio.isChecked():
            return IdleMode.Gnd

    @property
    def arc2Config(self):
        return ArC2Config(self.idleMode, self.controlMode)

    def __openFirmware(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self,\
            'Select firmware', os.path.dirname(sys.argv[0]),\
            "Firmware files (*.bin);;Any file (*.*)")[0]
        if fname is not None and len(fname) > 0:
            self.selectedFirmwareEdit.setText(os.path.realpath(fname))

    def __arc2Connect(self):
        if self._arc is not None:
            self.connectionArC2StatusLabel.setText("Disconnected")
            self.connectionArC2StatusLabel.setStyleSheet(_DISCONNECTED_LABEL_STYLE)
            del self._arc
            self._arc = None
            self.connectArC2Button.setText("Connect ArC2")
            self.connectionChanged.emit(False)
            self.selectedFirmwareEdit.setEnabled(True)
            self.selectFirmwareButton.setEnabled(True)
        else:
            thisdir = os.path.dirname(os.path.realpath(__file__))
            fw = os.path.realpath(self.selectedFirmwareEdit.text())
            self._arc = Instrument(0, fw)
            self.connectionArC2StatusLabel.setText("Connected")
            self.connectionArC2StatusLabel.setStyleSheet(_CONNECTED_LABEL_STYLE)
            self.connectArC2Button.setText("Disconnect ArC2")
            self.connectionChanged.emit(True)
            self.__controlModeChanged()
            self.__idleModeChanged()
            self.selectedFirmwareEdit.setEnabled(False)
            self.selectFirmwareButton.setEnabled(False)

    def disconnectArC2(self):
        if self._arc is not None:
            del self._arc
            self._arc = None

    @property
    def arc2(self):
        return self._arc
