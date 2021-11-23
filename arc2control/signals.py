from PyQt6.QtCore import QObject, pyqtSignal
from .h5utils import OpType
from numpy import ndarray, array


class Signals(QObject):
    # status changes
    arc2ConnectionChanged = pyqtSignal(bool, object)
    arc2ConfigChanged = pyqtSignal(object)
    crossbarSelectionChanged = pyqtSignal(set)
    readoutVoltageChanged = pyqtSignal(float)

    # value updates
    # wordline, bitline, current, voltage, pulse width, vread, optype
    valueUpdate = pyqtSignal(int, int, float, float, float, float, OpType)
    # same, but with ndarrays for bulk updates
    valueBulkUpdate = pyqtSignal(int, int, ndarray, ndarray, ndarray, ndarray, ndarray)
    # wordline, bitline
    dataDisplayUpdate = pyqtSignal(int, int)


__signals = Signals()


arc2ConnectionChanged = __signals.arc2ConnectionChanged
arc2ConfigChanged = __signals.arc2ConfigChanged
crossbarSelectionChanged = __signals.crossbarSelectionChanged
readoutVoltageChanged = __signals.readoutVoltageChanged

valueUpdate = __signals.valueUpdate
valueBulkUpdate = __signals.valueBulkUpdate
dataDisplayUpdate = __signals.dataDisplayUpdate

