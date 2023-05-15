from PyQt6 import QtCore, QtWidgets
from ..graphics import getPixmap
from ..version import __version__ as VERSION
from ..version import __copyright__ as COPYRIGHT
from h5py.version import version, hdf5_version
from platform import python_version, machine, platform, system
from . import GeneratedElements
try:
    from pyarc2 import LIBARC2_VERSION
except ImportError:
    LIBARC2_VERSION = "OLD"


class AboutDialog(GeneratedElements.Ui_AboutDialog, QtWidgets.QDialog):

    def __init__(self, parent=None):
        GeneratedElements.Ui_AboutDialog.__init__(self)
        QtWidgets.QDialog.__init__(self, parent=parent)
        self.setupUi(self)

        self.copyrightYearLabel.setText('© %s' % COPYRIGHT)
        self.logoLabel.setPixmap(getPixmap('splash'))
        self.pythonVersionLabel.setText('%s (%s %s)' % \
            (python_version(), system(), machine()))
        self.qtVersionLabel.setText(QtCore.QT_VERSION_STR)
        self.versionLabel.setText(VERSION)
        self.h5pyVersionLabel.setText("%s (%s)" % (version, hdf5_version))
        self.libarc2VersionLabel.setText(LIBARC2_VERSION)
