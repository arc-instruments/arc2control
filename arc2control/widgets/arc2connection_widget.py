import os.path
import sys
import time
import numpy as np
from PyQt6 import QtCore, QtWidgets
from . import GeneratedElements
from .. import constants
from ..arc2config import ArC2Config
from ..fwutils import discoverFirmwares
from ..mapper import ChannelMapper

from enum import Enum

from pyarc2 import Instrument, BiasOrder, ControlMode, ReadAt, \
    ReadAfter, DataMode, IdleMode, IODir, find_ids

_CONNECTED_LABEL_STYLE = "QLabel { color: white; background-color: green; font-weight: bold }"
_DISCONNECTED_LABEL_STYLE = "QLabel { color: white; background-color: #D11A1A; font-weight: bold }"


class ArC2ConnectionWidget(GeneratedElements.Ui_ArC2ConnectionWidget, QtWidgets.QWidget):

    arc2ConfigChanged = QtCore.pyqtSignal(ArC2Config)
    connectionChanged = QtCore.pyqtSignal(bool)
    mapperChanged = QtCore.pyqtSignal(ChannelMapper)
    firmwareSelectionChanged = QtCore.pyqtSignal(str)
    firmwareRequest = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        GeneratedElements.Ui_ArC2ConnectionWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setupUi(self)

        self.floatDevsRadio.toggled.connect(self.__idleModeChanged)
        self.softGndDevsRadio.toggled.connect(self.__idleModeChanged)
        self.hardGndDevsRadio.toggled.connect(self.__idleModeChanged)
        self.connectArC2Button.clicked.connect(self.__arc2Connect)
        self.refreshIDsButton.clicked.connect(self.__find_efm_ids)
        self.channelMapperComboBox.currentIndexChanged.connect(self.__mapperChanged)
        self.ioconfigComboBox.currentIndexChanged.connect(self.__ioconfigChanged)
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

    def __idleModeChanged(self, *args):

        if self._arc is None:
            return

        self._arc.finalise_operation(mode=self.arc2Config.idleMode)
        self.arc2ConfigChanged.emit(self.arc2Config)

    def __mapperChanged(self, idx):
        mapper = self.channelMapperComboBox.itemData(idx)
        self.ioconfigComboBox.clear()
        if mapper.ioconfs:
            for (_, v) in mapper.ioconfs.items():
                self.ioconfigComboBox.addItem(v['name'], v)
            self.ioconfigComboBox.setEnabled(True)
        else:
            self.ioconfigComboBox.setEnabled(False)
        self.mapperChanged.emit(mapper)
        self.__ioconfigChanged(self.ioconfigComboBox.currentIndex())

    def __ioconfigChanged(self, idx):

        data = self.ioconfigComboBox.itemData(idx)
        if data is None:
            return

        ios = data['ios']
        clusters = []
        # determine the IO directions from mapper
        # or default to outputs if the key is missing
        try:
            for d in data['dir']:
                val = d.lower().strip()
                if val == 'out':
                    clusters.append(IODir.OUT)
                elif val == 'in':
                    clusters.append(IODir.IN)
                else:
                    raise ValueError('Unknown IO Direction: %s' % val)
        except KeyError:
            clusters = [IODir.OUT, IODir.OUT, IODir.OUT, IODir.OUT]

        if len(clusters) < 4:
            raise ValueError('Incorrect IO cluster length; need 4, have %d' % len(clusters))

        if not np.issubdtype(type(ios), np.integer):
            raise ValueError('IO bitmask must be an integer')
        if ios < 0 or ios > 2**16 - 1:
            raise ValueError('IO bitmask out of bounds: min: 0; max 65535')

        if self._arc is None:
            return

        self._arc.set_logic(ios, *clusters)

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
        return ArC2Config(self.idleMode)

    def setMappers(self, mappers, default=None):

        defaultIndex = 0

        for (key, mapper) in sorted(mappers.items(), key=lambda v: v[1].name):
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
            self.__idleModeChanged()
            self.__ioconfigChanged(self.ioconfigComboBox.currentIndex())
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
