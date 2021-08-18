import abc

from PyQt6 import QtCore, QtWidgets
from .. import signals


class BaseOperation(QtCore.QThread):

    finished = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        if not isinstance(parent, BaseModule):
            raise TypeError("Parent is not a subclass of `BaseModule`")
        super().__init__(parent=parent)

        self.parent = parent

    @property
    def arc(self):
        return self.parent._arc()

    @property
    def cells(self):
        return self.parent._selectedCells

    @property
    def mapper(self):
        return self.parent._mapper

    @property
    def arc2Config(self):
        return self.parent._arcconf

    @abc.abstractmethod
    def run(self):
        pass


class BaseModule(QtWidgets.QWidget):

    def __init__(self, arcref, arcconf, vread, name, tag, cells, mapper, parent=None):
        super().__init__(parent=parent)

        self.name = name
        self.tag = tag
        self._arc = arcref
        self._arcconf = arcconf
        self._readoutVoltage = vread
        self._selectedCells = cells
        self._mapper = mapper

        signals.arc2ConnectionChanged.connect(self.__arc2ConnectionChanged)
        signals.crossbarSelectionChanged.connect(self.__crossbarSelectionChanged)
        signals.arc2ConfigChanged.connect(self.__arc2ConfigChanged)
        signals.readoutVoltageChanged.connect(self.__readoutVoltageChanged)

    @property
    def arc(self):
        """
        Return a reference to the currently active ArC2 instrument, or
        None, if no connection exists
        """
        try:
            return self._arc()
        # reference points to nothing
        except TypeError:
            return None

    @property
    def cells(self):
        """
        Return the currently selected cells
        """
        return self._selectedCells

    @property
    def mapper(self):
        """
        Return the current bit/word to channel mapping configuration
        """
        return self._mapper

    @property
    def arc2Config(self):
        """
        Return the current arc2 configuration
        """
        return self._arcconf

    @property
    def readoutVoltage(self):
        return self._readoutVoltage

    def __arc2ConnectionChanged(self, connected, ref):
        if connected:
            self._arc = ref
        else:
            self._arc = None

    def __crossbarSelectionChanged(self, cb):
        self._selectedCells = cb

    def __arc2ConfigChanged(self, config):
        self._arcconf = config

    def __readoutVoltageChanged(self, voltage):
        self._readoutVoltage = voltage
