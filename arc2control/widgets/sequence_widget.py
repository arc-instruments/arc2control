import PyQt6
import json
from PyQt6 import QtCore, QtGui, QtWidgets

from ..modules import moduleClassFromModName
from ..modules.base import BaseModule, modaction
from ..widgets.duration_widget import DurationWidget
from ..graphics import getIcon
from functools import partial


def _makeDeleteAction(parent=None):
    action = QtGui.QAction("Delete", parent)
    action.setIcon(getIcon('action-generic-delete'))

    return action


class PlacedModuleMimeData(QtCore.QMimeData):

    def __init__(self, mod):
        QtCore.QMimeData.__init__(self)
        self.setData('application/x-placed-module', b'')
        self.mod = mod

    def module(self):
        return self.mod


class PlacedLoopMimeData(QtCore.QMimeData):

    def __init__(self):
        QtCore.QMimeData.__init__(self)
        self.setData('application/x-placed-modloop', b'')


class PlacedSoftwareDelayMimeData(QtCore.QMimeData):

    def __init__(self):
        QtCore.QMimeData.__init__(self)
        self.setData('application/x-placed-software-delay', b'')


class DraggableButton(QtWidgets.QPushButton):

    deleteRequest = QtCore.pyqtSignal()

    def __init__(self, mod, parent=None):
        QtWidgets.QPushButton.__init__(self, mod.name, parent=parent)
        self.mod = mod

    @property
    def module(self):
        return self.mod

    def mouseMoveEvent(self, evt):
        if evt.buttons() != QtCore.Qt.MouseButton.LeftButton:
            return

        dragAction = QtGui.QDrag(self)
        dragAction.setMimeData(PlacedModuleMimeData(self.mod))

        dragAction.setHotSpot(evt.pos())
        dragAction.exec(QtCore.Qt.DropAction.MoveAction)

    def contextMenuEvent(self, evt):
        menu = QtWidgets.QMenu(self)
        deleteAction = _makeDeleteAction(self)
        deleteAction.triggered.connect(lambda: self.deleteRequest.emit())
        menu.addAction(deleteAction)
        menu.exec(evt.globalPos())


class IndicatorOverlay(QtWidgets.QWidget):

    def __init__(self, position, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.position = position
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, evt):
        painter = QtGui.QPainter(self)
        if self.position is not None:
            (x, y) = self.position
            width = self.parent().size().width()
            brush = QtGui.QBrush()
            brush.setColor(QtGui.QColor('blue'))
            brush.setStyle(QtCore.Qt.BrushStyle.SolidPattern)
            painter.fillRect(QtCore.QRect(0, y-2, width, 2), brush)
        painter.end()

    def update(self, position):
        if position != self.position:
            self.position = position
            self.repaint()


# This must be added to ``_INTERNAL_MODULES`` at the end of this file
class LoopSequenceWidget(BaseModule):

    deleteRequest = QtCore.pyqtSignal()

    def __init__(self, arc, arcconf, vread, store, cells, mapper, loops=1, parent=None):
        super().__init__(arc, arcconf, vread, store, 'LoopSequenceWidget', '_LSQW', \
            cells, mapper, parent=parent)
        self._loops = loops
        containerLayout = QtWidgets.QVBoxLayout()
        containerLayout.setSpacing(0)
        containerLayout.setContentsMargins(0, 0, 0, 0)

        self.header = QtWidgets.QFrame()
        self.header.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.header.customContextMenuRequested.connect(self._onShowContextMenu)
        self.header.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.header.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        headerLayout = QtWidgets.QHBoxLayout()
        headerLayout.setContentsMargins(3, 3, 3, 3)
        self.header.setStyleSheet('QFrame { background-color: #fff }')
        headerLayout.addItem(QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed))
        headerLayout.addWidget(QtWidgets.QLabel('Repeat'))
        self.loopSpinBox = QtWidgets.QSpinBox()
        self.loopSpinBox.setMinimum(1)
        self.loopSpinBox.setMaximum(999)
        self.loopSpinBox.setValue(self._loops)
        self.loopSpinBox.valueChanged.connect(self._onLoopValueChanged)
        self.loopSpinBox.setObjectName('loopSpinBox')
        headerLayout.addWidget(self.loopSpinBox)
        headerLayout.addWidget(QtWidgets.QLabel('times'))
        headerLayout.addItem(QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed))
        self.header.setLayout(headerLayout)

        self.body = QtWidgets.QFrame()
        self.body.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.body.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        bodyLayout = QtWidgets.QVBoxLayout()
        bodyLayout.setContentsMargins(0, 0, 0, 0)
        self.sequence = SequenceWidget(*self.modargs, parent=self)
        self.sequence.sequenceFinished.connect(self.onSequenceFinished)
        self.sequence.setObjectName('sequence')
        bodyLayout.addWidget(self.sequence)
        self.body.setLayout(bodyLayout)

        containerLayout.addWidget(self.header)
        containerLayout.addWidget(self.body)

        self.setLayout(containerLayout)

        self._generator = None

    def toJson(self):
        orig = json.loads(super().toJson())
        orig['widgets']['sequence'] = json.loads(self.sequence.toJson())
        return json.dumps(orig)

    def fromJson(self, fragment):
        super().fromJson(fragment)
        parsed = json.loads(fragment)
        seq = parsed['widgets']['sequence']
        self.sequence.fromJson(json.dumps(seq))

    @property
    def loops(self):
        return self._loops

    @property
    def isContainer(self):
        return True

    @property
    def module(self):
        return self

    def _debugPrint(self, level):
        self.sequence._debugPrint(level)

    def setApp(self, app):
        self.app = app
        self.sequence.setApp(self.app)

    def _onLoopValueChanged(self, value):
        self._loops = value

    def _onShowContextMenu(self, point):
        menu = QtWidgets.QMenu(self)
        deleteAction = _makeDeleteAction(self)
        deleteAction.triggered.connect(lambda: self.deleteRequest.emit())
        menu.addAction(deleteAction)
        menu.exec(self.mapToGlobal(point))

    def _nextLoopGenerator(self):
        for i in range(self._loops):
            yield i

    def onSequenceFinished(self):
        print(' >> Loop sequence finished')
        try:
            i = next(self._generator)
            print('Loop %d of %d' % (i+1, self._loops))
            self.sequence.execute()
        except StopIteration:
            print('Finished loops')
            self._generator = None
            self.experimentFinished.emit(-1, -1, '')

    def execute(self):
        print('Starting loop')
        self._generator = self._nextLoopGenerator()
        self.onSequenceFinished()

    def mouseMoveEvent(self, evt):
        if evt.buttons() != QtCore.Qt.MouseButton.LeftButton:
            return

        dragAction = QtGui.QDrag(self)
        dragAction.setMimeData(PlacedLoopMimeData())

        dragAction.setHotSpot(evt.pos())
        dragAction.exec(QtCore.Qt.DropAction.MoveAction)


# This must be added to ``_INTERNAL_MODULES`` at the end of this file
class SoftwareDelayWidget(BaseModule):

    deleteRequest = QtCore.pyqtSignal()

    def __init__(self, arc, arcconf, vread, store, cells, mapper, parent=None):

        BaseModule.__init__(self, arc, arcconf, vread, store, \
            'SoftwareDelay', '_SWD', cells, mapper, parent=parent)

        frame = QtWidgets.QFrame()
        frame.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        frame.customContextMenuRequested.connect(self._onShowContextMenu)
        frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        frameLayout = QtWidgets.QHBoxLayout()
        frameLayout.setContentsMargins(3, 3, 3, 3)

        frameLayout.addWidget(QtWidgets.QLabel('Wait for'))
        self.durationWidget = DurationWidget()
        self.durationWidget.setDurations([\
            ('ms', 1e-3), ('s', 1.0), ('min', 60.0)])
        self.durationWidget.setDuration(1, 's')
        self.durationWidget.setObjectName('delayDurationWidget')
        frameLayout.addWidget(self.durationWidget)
        frame.setLayout(frameLayout)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(frame)

        self.setLayout(layout)
        self._timer = None

    def _onShowContextMenu(self, point):
        menu = QtWidgets.QMenu(self)
        deleteAction = _makeDeleteAction(self)
        deleteAction.triggered.connect(lambda: self.deleteRequest.emit())
        menu.addAction(deleteAction)
        menu.exec(self.mapToGlobal(point))

    def mouseMoveEvent(self, evt):
        if evt.buttons() != QtCore.Qt.MouseButton.LeftButton:
            return

        dragAction = QtGui.QDrag(self)
        dragAction.setMimeData(PlacedSoftwareDelayMimeData())

        dragAction.setHotSpot(evt.pos())
        dragAction.exec(QtCore.Qt.DropAction.MoveAction)

    @property
    def module(self):
        return self

    @modaction('default', desc='Execute')
    def execute(self):
        if self._timer is not None:
            return
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.onTimerTimeout)
        self._timer.start(int(self.durationWidget.getDuration() * 1000))

    def onTimerTimeout(self):
        self._timer = None
        self.experimentFinished.emit(-1, -1, '')


class SequenceWidget(BaseModule):

    showWidget = QtCore.pyqtSignal(QtWidgets.QWidget)
    removeWidget = QtCore.pyqtSignal(BaseModule)
    sequenceChanged = QtCore.pyqtSignal(str)
    sequenceFinished = QtCore.pyqtSignal(list)


    def __init__(self, arc, arcconf, vread, store, cells, mapper, parent=None):
        super().__init__(arc, arcconf, vread, store, 'SequenceWidget', '_SQW', \
            cells, mapper, parent=parent)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setSpacing(2)
        self.layout.addItem(QtWidgets.QSpacerItem(20, 20,
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Expanding))
        self.setLayout(self.layout)
        self.topLevel = False
        self.setAcceptDrops(True)
        self.indicatorPosition = None
        self._parentSequence = None
        self._running = False
        self._generator = None
        self._activeSequence = []

        self.overlay = IndicatorOverlay(self.indicatorPosition, self)

    @property
    def isContainer(self):
        return True

    @property
    def module(self):
        return self

    def setTopLevel(self, topLevel):
        self.topLevel = topLevel

    def setApp(self, app):
        self.app = app

    def setParentSequence(self, seq):
        self._parentSequence = seq

    def dragEnterEvent(self, evt):
        evt.accept()

    def dragMoveEvent(self, evt):
        rect = evt.answerRect()
        (x, y) = (rect.x(), rect.y())

        self.insertPosition = self.layout.count() - 1
        indpos = None

        for i in range(self.layout.count() - 1):

            wdg = self.layout.itemAt(i).widget()

            try:
                container = wdg.isContainer
            except AttributeError:
                container = False

            if not container:
                checkTarget = wdg.size().height() // 2
            else:
                checkTarget = int(wdg.size().height() * 0.10)

            if y < wdg.y() + checkTarget:
                self.insertPosition = i
                indpos = (wdg.x(), wdg.y())
                self.overlay.update(self.indicatorPosition)
                break

        if indpos is None and self.layout.count() > 1:
            lastwdg = self.layout.itemAt(self.layout.count() - 1).widget()
            indpos = (wdg.x(), wdg.y() + wdg.height() + 3)

        self.indicatorPosition = indpos
        self.overlay.update(self.indicatorPosition)

        evt.accept()

    def dragLeaveEvent(self, evt):
        self.indicatorPosition = None
        self.insertPosition = None
        self.overlay.update(self.indicatorPosition)

    def mouseMoveEvent(self, evt):
        if evt.buttons() != QtCore.Qt.MouseButton.LeftButton:
            return

    def _addModuleButton(self, klass, position=None):
        if position is None:
            position = self.layout.count() - 1

        wdg = self.app().createModuleWidget(klass, withActions=False)
        wdg.layout().setContentsMargins(0, 0, 0, 0)
        button = DraggableButton(wdg.module)
        button.stackUnder(self.overlay)
        button.clicked.connect(partial(self.showWidget.emit, wdg))
        button.deleteRequest.connect(partial(self.deleteEntry, button))
        self.layout.insertWidget(position, button)

        return wdg

    def dropEvent(self, evt):

        def updatePositions(insert, indicator):
            self.insertPosition = insert
            self.indicatorPosition = indicator
            self.overlay.update(self.indicatorPosition)

        mime = evt.mimeData()

        # new module placement
        if mime.hasFormat('application/x-module'):
            (_, klass) = mime.moduleData()
            self._addModuleButton(klass)
            self.overlay.resize(self.size())
            evt.accept()
        # new loop placement
        elif mime.hasFormat('application/x-modloop'):
            frame = LoopSequenceWidget(*self.modargs, loops=1)
            frame.setApp(self.app)
            self.layout.insertWidget(self.insertPosition, frame)
            frame.sequence.showWidget.connect(self.showWidget)
            frame.sequence.removeWidget.connect(self.removeWidget)
            frame.sequence.setParentSequence(self)
            frame.deleteRequest.connect(partial(self.deleteEntry, frame))
            evt.accept()
        # new software delay
        elif mime.hasFormat('application/x-software-delay'):
            wdg = SoftwareDelayWidget(*self.modargs)
            wdg.deleteRequest.connect(partial(self.deleteEntry, wdg))
            self.layout.insertWidget(self.insertPosition, wdg)
            evt.accept()
        # change position
        elif any([m.startswith('application/x-placed') for m in mime.formats()]):
            src = evt.source()
            self.layout.removeWidget(src)
            if self.indicatorPosition is not None and self.indicatorPosition[1] > src.y():
                self.layout.insertWidget(self.insertPosition-1, src)
            else:
                self.layout.insertWidget(self.insertPosition, src)
            evt.accept()
        else:
            evt.ignore()

        updatePositions(None, None)

    def deleteEntry(self, wdg):
        if getattr(wdg, 'isContainer', False):
            for i in reversed(range(wdg.sequence.layout.count() - 1)):
                innerwdg = wdg.sequence.layout.itemAt(i).widget()
                wdg.sequence.deleteEntry(innerwdg)
        else:
            if hasattr(wdg, 'module'):
                self.removeWidget.emit(wdg.module)
        self.layout.removeWidget(wdg)
        wdg.setParent(None)
        wdg.deleteLater()

    def export(self):
        print(self.toJson())

    def importFile(self, fname):
        frag = open(fname, 'r').read()
        self.fromJson(frag)

    def toJson(self):
        orig = json.loads(super().toJson())

        orig['widgets'] = []

        for i in range(self.layout.count() - 1):
            wdg = self.layout.itemAt(i).widget()
            if getattr(wdg, 'isContainer', False):
                d = json.loads(wdg.toJson())
            else:
                d = json.loads(wdg.module.toJson())

            orig['widgets'].append(d)

        ret = json.dumps(orig, indent=2)
        return ret

    def fromJson(self, frag):

        raw = json.loads(frag)

        widgets = raw['widgets']
        try:
            name = raw['sequenceName']
        except KeyError:
            name = None

        for w in widgets:
            k = moduleClassFromModName(w['modname'])
            if k in _INTERNAL_MODULES:
                wdg = k(*self.modargs)
                wdg.setApp(self.app)
                if getattr(wdg, 'sequence', False):
                    wdg.sequence.showWidget.connect(self.showWidget)
                    wdg.sequence.removeWidget.connect(self.removeWidget)
                wdg.deleteRequest.connect(partial(self.deleteEntry, wdg))
                wdg.fromJson(json.dumps(w))
                self.layout.insertWidget(self.layout.count() - 1, wdg)
            else:
                wdg = self._addModuleButton(k)
                wdg.module.fromJson(json.dumps(w))

        self.sequenceChanged.emit(name)

    def _nextWidgetGenerator(self):
        for i in range(self.layout.count() - 1):
            wdg = self.layout.itemAt(i).widget()
            print('Getting next widget ' + repr(wdg.module))

            if i == 0:
                previousWdg = None
            else:
                previousWdg = self.layout.itemAt(i-1).widget()

            yield (previousWdg, wdg)

    def appendResult(self, what):
        if self._parentSequence is None:
            self._activeSequence.append(what)
        else:
            self._parentSequence.appendResult(what)

    def _debugPrint(self, level=0):
        for i in range(self.layout.count() - 1):
            wdg = self.layout.itemAt(i).widget()

            if getattr(wdg, 'isContainer', False):
                wdg._debugPrint(level+1)
            else:
                print('%s' % ''.join([' ']*level), wdg.module)

    def onExperimentFinished(self, *args):

        print(' > Experiment finished', self)

        if not self._running:
            return

        try:
            prevResult = (args[0], args[1], args[2])
        except IndexError:
            prevResult = None

        if prevResult is not None and prevResult[2] != '':
            self.appendResult(prevResult)

        try:
            (prevwdg, wdg) = next(self._generator)
            print(prevwdg, wdg)

            if prevwdg is not None:
                prevwdg.module.experimentFinished.disconnect(prevwdg._finishedSlot)

            if getattr(wdg, 'isContainer', False):
                slot = wdg.experimentFinished.connect(self.onExperimentFinished)
                setattr(wdg, '_finishedSlot', slot)
                print('Running container ' + repr(wdg))
                wdg.execute()
                return

            try:
                mod = wdg.module
                if 'selection' in mod.actions().keys():
                    (_, fn, _) = mod.actions()['selection']
                elif 'default' in mod.actions().keys():
                    (_, fn, _) = mod.actions()['default']
                else:
                    raise KeyError('selection/default')

                slot = mod.experimentFinished.connect(self.onExperimentFinished)
                setattr(wdg, '_finishedSlot', slot)
                print('Running ' + repr(mod))
                fn(mod)
            except KeyError as ke:
                self.logger.warn('No selection key')
            except AttributeError as exc:
                self.logger.warn('No attribute ' + str(exc))

        except StopIteration:
            self._generator = None
            self._running = False
            lastidx = self.layout.count() - 2
            lastwdg = self.layout.itemAt(lastidx).widget()
            lastwdg.module.experimentFinished.\
                disconnect(lastwdg._finishedSlot)

            self.sequenceFinished.emit(self._activeSequence)

    def execute(self):

        self._generator = self._nextWidgetGenerator()
        self._activeSequence = []
        self._running = True

        self.onExperimentFinished([])


_INTERNAL_MODULES = [
    LoopSequenceWidget,
    SoftwareDelayWidget
]

