# toplevel module

from .version import __version__ as VERSION

from PyQt6 import QtCore

ArC2ControlSettings = QtCore.QSettings('ArCInstruments', 'ArC2Control')
