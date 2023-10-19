import PyQt6
from PyQt6 import QtCore, QtGui, QtWidgets
from . import GeneratedElements
from .sequence_widget import SequenceWidget
from ..graphics import getIcon
from .. import constants
from datetime import datetime
from .. import createLogger
logger = createLogger('_SQR')
import base64
import random
import json

from functools import partial


class ModuleMimeData(QtCore.QMimeData):

    def __init__(self, name, klass):
        QtCore.QMimeData.__init__(self)
        self.setData('application/x-module', b'')
        self.name = name
        self.klass = klass

    @property
    def mimeName(self):
        return self.name

    def moduleData(self):
        return (self.name, self.klass)


class LoopMimeData(QtCore.QMimeData):

    def __init__(self):
        QtCore.QMimeData.__init__(self)
        self.setData('application/x-modloop', b'')

    @property
    def mimeName(self):
        return 'Loop'

class SoftwareDelayMimeData(QtCore.QMimeData):

    def __init__(self):
        QtCore.QMimeData.__init__(self)
        self.setData('application/x-software-delay', b'')

    @property
    def mimeName(self):
        return 'Software Delay'


class DraggableLabel(QtWidgets.QLabel):

    def __init__(self, mimeName, mimeKlass, mimeArgs, parent=None):
        QtWidgets.QLabel.__init__(self, mimeName, parent=parent)
        self.mimeKlass = mimeKlass
        self.mimeArgs = mimeArgs
        self.setStyleSheet('QLabel { padding: 5px; background-color: #F0F8FF; border: 1px solid black; }')
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

    def mouseMoveEvent(self, evt):
        if evt.buttons() != QtCore.Qt.MouseButton.LeftButton:
            return

        dragAction = QtGui.QDrag(self)
        mime = self.mimeKlass(*self.mimeArgs)
        dragAction.setMimeData(mime)

        dragAction.setHotSpot(evt.pos())
        dragAction.exec(QtCore.Qt.DropAction.MoveAction)


class ExperimentListWidget(QtWidgets.QWidget):

    def __init__(self, modules=None, parent=None):

        QtWidgets.QWidget.__init__(self, parent=parent)

        if modules is None:
            self.modules = {}
        else:
            self.modules = modules

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        for (_, (name, klass)) in self.modules.items():
            mimeKlass = ModuleMimeData
            mimeArgs = (name, klass)
            layout.addWidget(DraggableLabel(name, mimeKlass, mimeArgs))
        self.setLayout(layout)


class FlowListWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):

        QtWidgets.QWidget.__init__(self, parent=parent)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(DraggableLabel('Loop', LoopMimeData, ()))
        layout.addWidget(DraggableLabel('SoftwareDelay', SoftwareDelayMimeData, ()))
        self.setLayout(layout)


class SequencerWidget(QtWidgets.QWidget, GeneratedElements.Ui_SequencerWidget):

    def __init__(self, state, parent=None):

        GeneratedElements.Ui_SequencerWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.state = state
        self.modules = state['modules']
        self.app = state['app']

        self.setupUi(self)
        self.__setupWidgets()

    def __setupWidgets(self):

        self.horizontalSpacer = QtWidgets.QSpacerItem(0, 20,
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self.horizontalLayout.addItem(self.horizontalSpacer)
        self.sequenceWidget = self.app().createBareModuleObject(SequenceWidget, withEvents=False)
        self.sequenceWidget.showWidget.connect(self.showWidget)
        self.sequenceWidget.removeWidget.connect(self.removeWidget)
        self.sequenceWidget.setApp(self.app)
        self.sequenceWidget.setTopLevel(True)
        self.sequenceWidget.sequenceFinished.connect(self.onSequenceFinished)
        self.sequenceWidget.sequenceChanged.connect(self.onSequenceChanged)
        self.sequenceScrollArea.setWidget(self.sequenceWidget)

        containerLayout = QtWidgets.QVBoxLayout()
        containerLayout.setContentsMargins(0, 0, 0, 0)
        self.moduleContainerWidget.setLayout(containerLayout)

        self.experimentListWidget = ExperimentListWidget(self.modules)
        self.widgetListCollapsibleTreeWidget.addWidget("Modules", \
            self.experimentListWidget)

        self.flowListWidget = FlowListWidget()
        self.widgetListCollapsibleTreeWidget.addWidget("Execution Flow", \
            self.flowListWidget)

        self.executeButton.clicked.connect(self._executeClicked)
        self.exportButton.clicked.connect(self._exportClicked)
        self.importButton.clicked.connect(self._importClicked)

        self.showModulePanel(False)
        self.expandContainerWidgetButton.clicked.connect(self.toggleModulePanel)

        self.generateNameButton.setIcon(getIcon('random'))
        self.generateNameButton.clicked.connect(self.generateSequenceName)
        self.generateSequenceName()

    def showWidget(self, wdg):
        if not hasattr(wdg, 'module'):
            return

        self.showModulePanel(True)
        layout = self.moduleContainerWidget.layout()
        if layout.count() > 0:
            currentWidget = layout.itemAt(0).widget()
            layout.removeWidget(currentWidget)
            currentWidget.hide()
        layout.addWidget(wdg)
        wdg.show()

    def generateSequenceName(self):
        suffix = base64.b16encode(random.randbytes(4)).decode()
        name = "SEQ_%s" % (suffix)
        self.sequenceNameLineEdit.setText(name)

    def removeWidget(self, mod):
        layout = self.moduleContainerWidget.layout()
        if layout.count() > 0:
            wdg = layout.itemAt(0).widget()
            if mod == layout.itemAt(0).widget().module:
                layout.removeWidget(wdg)
                wdg.setParent(None)
                wdg.deleteLater()
                self.showModulePanel(False)

    def showModulePanel(self, show):
        if show:
            self.horizontalSpacer.changeSize(0, 0,
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed)
            self.moduleContainerWidget.setVisible(True)
            self.expandContainerWidgetButton.setText('◀')
        else:
            self.moduleContainerWidget.setVisible(False)
            self.expandContainerWidgetButton.setText('▶')
            self.horizontalSpacer.changeSize(0, 20,
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed)

    def toggleModulePanel(self):
        now = self.moduleContainerWidget.isVisible()
        self.showModulePanel(not now)

    def onSequenceFinished(self, experiments):
        datastore = self.state['store']()
        logger.info('SEQUENCER END')
        print(experiments)
        datastore.make_sequence_group(self.sequenceNameLineEdit.text(), experiments)

    def onSequenceChanged(self, name):
        if name is None:
            self.sequenceNameLineEdit.setText(self.generateSequenceName())
        else:
            self.sequenceNameLineEdit.setText(name)

        self.sequenceNameLineEdit.selectAll()

    def _executeClicked(self):
        logger.info('SEQUENCER START')
        print('++++')
        self.sequenceWidget._debugPrint()
        print('++++')
        self.sequenceWidget.execute()

    def _exportClicked(self):
        data = json.loads(self.sequenceWidget.toJson())
        data['sequenceName'] = self.sequenceNameLineEdit.text()

        fname = QtWidgets.QFileDialog.getSaveFileName(self, "Export Sequence Data",\
            '', constants.MOD_FILE_FILTER)

        if fname is None or len(fname[0]) == 0:
            return

        with open(fname[0], 'w') as out:
            json.dump(data, out, indent=2)

    def _importClicked(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, "Open Widget Data",\
            '', constants.MOD_FILE_FILTER)

        if fname is None or len(fname[0]) == 0:
            return

        self.sequenceWidget.importFile(fname[0])
