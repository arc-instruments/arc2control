from PyQt6 import QtCore


class Signals(QtCore.QObject):
    arc2ConnectionChanged = QtCore.pyqtSignal(bool, object)
    arc2ConfigChanged = QtCore.pyqtSignal(object)
    crossbarSelectionChanged = QtCore.pyqtSignal(set)


__signals = Signals()


arc2ConnectionChanged = __signals.arc2ConnectionChanged
arc2ConfigChanged = __signals.arc2ConfigChanged
crossbarSelectionChanged = __signals.crossbarSelectionChanged

