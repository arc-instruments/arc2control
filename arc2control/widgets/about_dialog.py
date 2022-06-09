from PyQt6 import QtCore, QtWidgets
from .generated.about import Ui_AboutDialog
from ..graphics import getPixmap
from ..version import __version__ as VERSION
from ..version import __copyright__ as COPYRIGHT
from platform import python_version, machine, platform, system


class AboutDialog(Ui_AboutDialog, QtWidgets.QDialog):

    def __init__(self, parent=None):
        Ui_AboutDialog.__init__(self)
        QtWidgets.QDialog.__init__(self, parent=parent)
        self.setupUi(self)

        self.copyrightYearLabel.setText('©%s' % COPYRIGHT)
        self.logoLabel.setPixmap(getPixmap('splash'))
        self.pythonVersionLabel.setText('%s on %s %s' % \
            (python_version(), system(), machine()))
        self.qtVersionLabel.setText(QtCore.QT_VERSION_STR)
        self.versionLabel.setText(VERSION)
