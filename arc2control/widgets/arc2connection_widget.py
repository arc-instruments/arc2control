import os.path
import sys
import time
import numpy as np
from PyQt6 import QtCore, QtWidgets
from .generated.arc2connection import Ui_ArC2ConnectionWidget
from .. import constants
from ..fwutils import discoverFirmwares
from ..mapper import ChannelMapper

from enum import Enum

from pyarc2 import Instrument, BiasOrder, ControlMode, ReadAt, \
    ReadAfter, DataMode, IdleMode, ArC2Config, find_ids

_CONNECTED_LABEL_STYLE = "QLabel { color: white; background-color: green; font-weight: bold }"
_DISCONNECTED_LABEL_STYLE = "QLabel { color: white; background-color: #D11A1A; font-weight: bold }"


class ArC2ConnectionWidget(Ui_ArC2ConnectionWidget, QtWidgets.QWidget):

    arc2ConfigChanged = QtCore.pyqtSignal(ArC2Config)
    connectionChanged = QtCore.pyqtSignal(bool)
    mapperChanged = QtCore.pyqtSignal(ChannelMapper)
    firmwareSelectionChanged = QtCore.pyqtSignal(str)
    firmwareRequest = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        Ui_ArC2ConnectionWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setupUi(self)

        self.internalControlRadio.toggled.connect(self.__controlModeChanged)
        self.headerControlRadio.toggled.connect(self.__controlModeChanged)
        self.floatDevsRadio.toggled.connect(self.__idleModeChanged)
        self.softGndDevsRadio.toggled.connect(self.__idleModeChanged)
        self.hardGndDevsRadio.toggled.connect(self.__idleModeChanged)
        self.connectArC2Button.clicked.connect(self.__arc2Connect)
        self.refreshIDsButton.clicked.connect(self.__find_efm_ids)
        self.channelMapperComboBox.currentIndexChanged.connect(self.__mapperChanged)
        self.__find_efm_ids()
        self.refreshFirmwares()

        self._arc = None

    def __find_efm_ids(self):
        self.efmIDsComboBox.clear()
        for i in find_ids():
            self.efmIDsComboBox.addItem('%2d' % i, i)

    def refreshFirmwares(self):
        self.firmwareComboBox.clear()
        fws = discoverFirmwares()
        for (k, v) in reversed(sorted(fws.items())):
            if v['verified']:
                self.firmwareComboBox.addItem(k, v['path'])

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

        self._arc.finalise_operation(mode=self.arc2Config.idleMode)
        self.arc2ConfigChanged.emit(self.arc2Config)

    def __mapperChanged(self, idx):
        mapper = self.channelMapperComboBox.itemData(idx)
        self.mapperChanged.emit(mapper)

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
        if self.softGndDevsRadio.isChecked():
            return IdleMode.SoftGnd
        if self.hardGndDevsRadio.isChecked():
            return IdleMode.HardGnd

    @property
    def arc2Config(self):
        return ArC2Config(self.idleMode, self.controlMode)

    def setMappers(self, mappers, default=None):

        defaultIndex = 0

        for (key, mapper) in mappers.items():
            self.channelMapperComboBox.addItem(mapper.name, mapper)
            # if a default value is selected check if this is the one
            if default is not None and key == default:
                defaultIndex = self.channelMapperComboBox.count() - 1

        self.channelMapperComboBox.setCurrentIndex(defaultIndex)

    def currentMapper(self):
        return self.channelMapperComboBox.currentData()

    def __arc2Connect(self):

        if self.efmIDsComboBox.count() == 0:
            QtWidgets.QMessageBox.critical(self, \
                'Connect ArC2', \
                'No tools found. Connect an ArC TWO and click the refresh button')

        if self.firmwareComboBox.count() == 0:
            resp = QtWidgets.QMessageBox.question(self, \
                'Connect ArC2', \
                'No suitable firmware found. Open the firmware manager?')

            if resp == QtWidgets.QMessageBox.StandardButton.Yes:
                self.firmwareRequest.emit()
            return

        if self._arc is not None:
            self.connectionArC2StatusLabel.setText("Disconnected")
            self.connectionArC2StatusLabel.setStyleSheet(_DISCONNECTED_LABEL_STYLE)
            del self._arc
            self._arc = None
            self.connectArC2Button.setText("Connect ArC2")
            self.connectionChanged.emit(False)
            self.firmwareComboBox.setEnabled(True)
            self.efmIDsComboBox.setEnabled(True)
            self.refreshIDsButton.setEnabled(True)
        else:
            fw = self.firmwareComboBox.currentData()
            efmid = self.efmIDsComboBox.currentData()
            if not os.path.exists(fw):
                QtWidgets.QMessageBox.critical(self, \
                    'Connect ArC2', \
                    'Firmware file %s does not exist' % os.path.basename(fw))
                return
            try:
                self._arc = Instrument(efmid, fw)
            except:
                return
            self.connectionArC2StatusLabel.setText("Connected")
            self.connectionArC2StatusLabel.setStyleSheet(_CONNECTED_LABEL_STYLE)
            self.connectArC2Button.setText("Disconnect ArC2")
            self.connectionChanged.emit(True)
            self.__controlModeChanged()
            self.__idleModeChanged()
            self.efmIDsComboBox.setEnabled(False)
            self.firmwareComboBox.setEnabled(False)
            self.refreshIDsButton.setEnabled(False)

    def disconnectArC2(self):
        if self._arc is not None:
            del self._arc
            self._arc = None

    @property
    def arc2(self):
        return self._arc
