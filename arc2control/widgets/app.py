import PyQt6
from PyQt6 import QtCore, QtWidgets
from .generated.mainwindow import Ui_ArC2MainWindow

import sys
import time
import os.path
import shutil
import numpy as np
from functools import partial
import pyqtgraph as pg
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

from pyarc2 import Instrument, BiasOrder, ControlMode, ReadAt, \
    ReadAfter, DataMode, IdleMode
from .common import Polarity
from .arc2connection_widget import ArC2ConnectionWidget
from .readops_widget import ReadOpsWidget
from .pulseops_widget import PulseOpsWidget
from .plottingoptions_widget import DisplayType as PlotDisplayType
from .plottingoptions_widget import YScale as PlotYScale
from .plottingoptions_widget import PlottingOptionsWidget
from .device_explorer_widget import DeviceExplorerWidget
from .. import graphics
from ..h5utils import H5DataStore, OpType, H5Mode
import weakref
import os, tempfile
from .. import signals
from ..modules import moduleClassFromJson


_APP_TITLE = 'ArC2 Control Panel'
_H5_FILE_FILTER = 'Datasets (*.h5);;All files (*.*)'
_H5_TS_EXPORT_FILTER = 'Comma separated file (*.csv);;Tab separated file (*.tsv)'
_MOD_FILE_FILTER = 'JSON files (*.json);;All files (*.*)'


class App(Ui_ArC2MainWindow, QtWidgets.QMainWindow):

    def __init__(self, mapping, modules={}, parent=None):
        self._arc = None
        self.mapper = mapping
        self._modules = modules
        Ui_ArC2MainWindow.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setupUi(self)
        self.__setupControlWidgets()

        self.deviceExplorerWidget = DeviceExplorerWidget()
        self.deviceExplorerWidget.setTagMapper(\
            {key: self._modules[key][0] for key in self._modules.keys()})
        self.deviceDockWidget.setWidget(self.deviceExplorerWidget)

        self.__setupPlottingWidgets()
        self.__populateModuleComboBox()
        self.__loadIcons()

        self._datastore = H5DataStore(tempfile.NamedTemporaryFile(\
            suffix='.h5', delete=False).name,\
            mode=H5Mode.WRITE)
        self._datastore.__setattr__('is_temporary', True)

        self.__connectSignals()

        # initialise an empty crossbar (all zeros)
        self.crossbarRefresh(np.zeros(self._datastore.shape),\
            np.zeros(self._datastore.shape))

        self.setWindowTitle('%s [%s]' % \
            (_APP_TITLE, os.path.basename(self._datastore.fname)))
        self.resize(950, 800)

        self.show()

    def __connectSignals(self):

        self.selectAllButton.clicked.connect(lambda: self.mainCrossbarWidget.selectAll())

        self.mainCrossbarWidget.selectionChanged.connect(self.selectionChanged)
        self.mainCrossbarWidget.mousePositionChanged.connect(self.mousePositionChanged)
        self.readOpsWidget.readSelectedClicked.connect(self.readSelectedClicked)
        self.readOpsWidget.readAllClicked.connect(self.readAllClicked)
        self.readOpsWidget.readoutVoltageChanged.connect(self.readoutVoltageChanged)
        self.arc2ConnectionWidget.connectionChanged.connect(self.connectionChanged)
        self.arc2ConnectionWidget.arc2ConfigChanged.connect(signals.arc2ConfigChanged.emit)

        self.pulseOpsWidget.positivePulseClicked.connect(\
            partial(self.pulseSelectedClicked, polarity=Polarity.POSITIVE))
        self.pulseOpsWidget.negativePulseClicked.connect(\
            partial(self.pulseSelectedClicked, polarity=Polarity.NEGATIVE))
        self.pulseOpsWidget.positivePulseReadClicked.connect(\
            partial(self.pulseReadSelectedClicked, polarity=Polarity.POSITIVE))
        self.pulseOpsWidget.negativePulseReadClicked.connect(\
            partial(self.pulseReadSelectedClicked, polarity=Polarity.NEGATIVE))

        self.plottingOptionsWidget.xRangeChanged.connect(self.refreshCurrentPlot)
        self.plottingOptionsWidget.displayTypeChanged.connect(self.refreshCurrentPlot)
        self.plottingOptionsWidget.yScaleChanged.connect(self.changePlotScale)

        self.newDatasetAction.triggered.connect(self.newDataset)
        self.openDatasetAction.triggered.connect(self.openDataset)
        self.saveDatasetAction.triggered.connect(self.saveDataset)
        self.saveDatasetAsAction.triggered.connect(self.saveDatasetAs)
        self.quitAction.triggered.connect(self.close)

        self.selectionChanged(self.mainCrossbarWidget.selection)

        self.deviceExplorerWidget.experimentSelected.connect(self.experimentSelected)
        self.deviceExplorerWidget.exportDeviceHistoryRequested.connect(self.__exportTimeSeries)

        signals.valueUpdate.connect(self.valueUpdate)
        signals.valueBulkUpdate.connect(self.valueUpdateBulk)
        signals.dataDisplayUpdate.connect(self.updateSinglePlot)

    def __setupControlWidgets(self):
        self.arc2ConnectionWidget = ArC2ConnectionWidget()
        self.readOpsWidget = ReadOpsWidget()
        self.pulseOpsWidget = PulseOpsWidget()
        self.plottingOptionsWidget = PlottingOptionsWidget()

        self.controlCollapsibleTreeWidget.addWidget("ArC2 Connection",\
            self.arc2ConnectionWidget)
        self.controlCollapsibleTreeWidget.addWidget("Read Operations",\
            self.readOpsWidget)
        self.controlCollapsibleTreeWidget.addWidget("Pulse Operations",\
            self.pulseOpsWidget)
        self.controlCollapsibleTreeWidget.addWidget("Plotting Options",\
            self.plottingOptionsWidget)

    def __setupPlottingWidgets(self):
        self.tracePlot = self.mainPlotWidget.addPlot(name='trace')
        self.tracePlot.showGrid(x=True, y=True)
        self.tracePlot.getAxis('left').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.tracePlot.getAxis('left').setGrid(50)
        self.tracePlot.getAxis('bottom').setGrid(50)
        self.tracePlot.getAxis('left').setLabel('Resistance', units='Ω')
        self.tracePlot.getAxis('right').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.mainPlotWidget.nextRow()
        self.pulsePlot = self.mainPlotWidget.addPlot(name='pulse')
        self.pulsePlot.showGrid(x=True, y=True)
        self.pulsePlot.getAxis('left').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.pulsePlot.getAxis('left').setGrid(50)
        self.pulsePlot.getAxis('bottom').setGrid(50)
        self.pulsePlot.getAxis('left').setLabel('Amplitude', units='V')
        self.pulsePlot.getAxis('right').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.pulsePlot.setXLink('trace')
        self.pulsePlot.getAxis('bottom').setLabel('Pulse')
        self.mainPlotWidget.ci.layout.setRowStretchFactor(0, 2)
        self.mainPlotWidget.ci.layout.setRowStretchFactor(1, 1)

    def __populateModuleComboBox(self):
        for (tag, (name, mod)) in self._modules.items():
            self.moduleListComboBox.addItem(name, mod)

        self.addModuleButton.clicked.connect(self.addModuleClicked)
        self.removeModuleButton.clicked.connect(self.removeCurrentModuleTab)
        self.saveModuleButton.clicked.connect(self.saveModuleClicked)
        self.loadModuleButton.clicked.connect(self.loadModuleClicked)

    def __loadIcons(self):
        self.setWindowIcon(graphics.getIcon('arc2-logo'))
        self.openDatasetAction.setIcon(graphics.getIcon('action-open'))
        self.saveDatasetAction.setIcon(graphics.getIcon('action-save'))
        self.saveDatasetAsAction.setIcon(graphics.getIcon('action-save-as'))
        self.newDatasetAction.setIcon(graphics.getIcon('action-new-dataset'))
        self.quitAction.setIcon(graphics.getIcon('action-exit'))

    def connectionChanged(self, connected):
        if connected:
            self._arc = weakref.ref(self.arc2ConnectionWidget.arc2)
        else:
            self._arc = None
        signals.arc2ConnectionChanged.emit(connected, self._arc)

    def experimentSelected(self, tag, path):
        try:
            dset = self._datastore.dataset(path)
            mod = self._modules[tag][1]
            wdg = mod.display(dset)

            if wdg is None:
                print('display method exists, but no Widget is produced', \
                    file=sys.stderr)
                return

            dialog = QtWidgets.QDialog(self)
            dialog.setWindowIcon(graphics.getIcon('arc2-logo'))
            dtitle = wdg.property('title')
            if dtitle is None:
                dtitle = path
            dialog.setWindowTitle(dtitle)

            layout = QtWidgets.QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(wdg)
            dialog.setLayout(layout)

            (recw, rech) = wdg.property('recsize')

            if (recw, rech) != (None, None):
                dialog.resize(recw, rech)

            dialog.show()

        except KeyError as err:
            print('Could not retrieve dataset or associated module:', err)

    def selectionChanged(self, cells):
        # cells = self.mainCrossbarWidget.selectedCells

        signals.crossbarSelectionChanged.emit(cells)

        if len(cells) == 0:
            self.readOpsWidget.setReadSelectedEnabled(False)
            self.pulseOpsWidget.setPulseEnabled(Polarity.POSITIVE, False)
            self.pulseOpsWidget.setPulseEnabled(Polarity.NEGATIVE, False)
            self.pulseOpsWidget.setPulseReadEnabled(Polarity.POSITIVE, False)
            self.pulseOpsWidget.setPulseReadEnabled(Polarity.NEGATIVE, False)
        else:
            self.readOpsWidget.setReadSelectedEnabled(True)
            self.pulseOpsWidget.setPulseEnabled(Polarity.POSITIVE, True)
            self.pulseOpsWidget.setPulseEnabled(Polarity.NEGATIVE, True)
            self.pulseOpsWidget.setPulseReadEnabled(Polarity.POSITIVE, True)
            self.pulseOpsWidget.setPulseReadEnabled(Polarity.NEGATIVE, True)

        if len(cells) != 1:
            return
        else:
            cell = list(cells)[0]
            value = self.mainCrossbarWidget.valueOf(cell)
            self.readOpsWidget.setValue(cell.w, cell.b, value, suffix='Ω')
            self.updateSinglePlot(*list(cells)[0])

    def mousePositionChanged(self, cell):
        if cell.w < 0 or cell.b < 0:
            self.hoverLabel.setText("")
            return

        (w, b) = (cell.w, cell.b)
        value = self.mainCrossbarWidget.valueOf(cell)
        if not np.isnan(value):
            value = pg.siFormat(value, suffix='Ω')
        else:
            value = "N/A"
        self.hoverLabel.setText("W = %d | B = %d – %s" % (cell.w+1, cell.b+1, value))

    def readoutVoltageChanged(self, voltage):
        signals.readoutVoltageChanged.emit(voltage)

    def readSelectedClicked(self):
        cells = self.mainCrossbarWidget.selectedCells
        if len(cells) != 1:
            self.readSelectedSlices(cells)
        else:
            self.readSelectedCell(cells)

    def __pulseOpInner(self, voltage, pulsewidth, _single, _slice, _all):
        cells = self.mainCrossbarWidget.selectedCells

        # first check if we can use the Pulse{Read}All operation
        # from libarc2, this can only be applied to the full
        # crossbar
        if len(cells) == self.mapper.total_devices:
            _all(voltage, pulsewidth)
        # otherwise either do single pulse or slice pulse
        else:
            if len(cells) != 1:
                _slice(cells, voltage, pulsewidth)
            else:
                _single(cells, voltage, pulsewidth)


    def pulseSelectedClicked(self, polarity):

        _single = self.pulseSelectedCell
        _slice = self.pulseSelectedSlices
        _all = self.pulseAll

        if polarity == Polarity.POSITIVE:
            (v, pw) = self.pulseOpsWidget.positiveParams()
        elif polarity == Polarity.NEGATIVE:
            (v, pw) = self.pulseOpsWidget.negativeParams()
        else:
            raise Exception("Unknown polarity?")

        self.__pulseOpInner(v, pw, _single, _slice, _all)

    def pulseReadSelectedClicked(self, polarity):
        vread = self.readOpsWidget.readoutVoltage()
        _single = partial(self.pulseReadSelectedCell, vread=vread)
        _slice = partial(self.pulseReadSelectedSlices, vread=vread)
        _all = partial(self.pulseReadAll, vread=vread)

        if polarity == Polarity.POSITIVE:
            (v, pw) = self.pulseOpsWidget.positiveParams()
        elif polarity == Polarity.NEGATIVE:
            (v, pw) = self.pulseOpsWidget.negativeParams()
        else:
            raise Exception("Unknown polarity?")

        self.__pulseOpInner(v, pw, _single, _slice, _all)

    def pulseReadSelectedCell(self, cells, vpulse, pulsewidth, vread):
        cell = cells[0]
        (w, b) = (cell.w, cell.b)
        (high, low) = self.mapper.wb2ch[w][b]
        print("pulseread (word: %2d bit: %2d ←→ low: %2d high: %2d)" % (w, b, low, high))
        print("pulseread (V = %g, PW = %g ns)" % (vpulse, pulsewidth*1.0e9))
        if self._arc is None:
            print("arc2 is not connected")
        else:
            current = self._arc().pulseread_one(low, high, vpulse, int(pulsewidth*1.0e9),
                vread)
            self.__finaliseOperation()
            #self.mainCrossbarWidget.updateData(w, b, np.abs(vread/current))
            self.readOpsWidget.setValue(w, b, np.abs(vread/current))
            signals.valueUpdate.emit(w, b, current, vpulse, pulsewidth, vread,\
                OpType.PULSEREAD)
        signals.dataDisplayUpdate.emit(w, b)

    def pulseReadSelectedSlices(self, cells, vpulse, pulsewidth, vread):
        slices = {}

        data = self.mainCrossbarWidget.data.T

        for c in cells:
            try:
                slices[c.b].append(c.w)
            except KeyError:
                slices[c.b] = [c.w]

        for (k, v) in slices.items():
            try:
                (volt, curr, idx) = self.__pulseReadSlice(self.mapper.b2ch[k],
                    np.array([self.mapper.w2ch[x] for x in v], dtype=np.uint64),
                    vpulse, pulsewidth)
                data[k][idx] = np.abs(volt/curr[idx])
                for w in idx:
                    signals.valueUpdate.emit(w, k, curr[w], volt, \
                        pulsewidth, self.readOpsWidget.readoutVoltage(),\
                        OpType.PULSEREAD)
            except TypeError:
                # arc not connected
                return

        self.mainCrossbarWidget.setData(data.T)

    def pulseReadAll(self, vpulse, pulsewidth, vread):
        if self._arc is None:
            print("arc2 is not connected")
            return

        voltage = self.readOpsWidget.readoutVoltage()
        raw = self._arc().pulseread_all(vpulse, int(pulsewidth*1.0e9), voltage,
            BiasOrder.Cols)
        self.__finaliseOperation()
        data = np.empty(shape=(self.mapper.nbits, self.mapper.nwords))
        for (row, channel) in enumerate(sorted(self.mapper.ch2b.keys())):
            bitline = self.mapper.ch2b[channel]
            data[bitline] = voltage/np.abs(raw[row][self.mapper.word_idxs])

        self.mainCrossbarWidget.setData(data.T)

    def readSelectedSlices(self, cells):

        slices = {}

        data = self.mainCrossbarWidget.data.T

        for c in cells:
            try:
                slices[c.b].append(c.w)
            except KeyError:
                slices[c.b] = [c.w]

        for (k, v) in slices.items():
            try:
                (volt, curr, idx) = self.__readSlice(self.mapper.b2ch[k],
                    np.array([self.mapper.w2ch[x] for x in v], dtype=np.uint64))
                data[k][idx] = np.abs(volt/curr[idx])
                for w in idx:
                    signals.valueUpdate.emit(w, k, curr[w], volt, 0.0,\
                        volt, OpType.READ)
            except TypeError:
                # arc not connected
                return

        self.mainCrossbarWidget.setData(data.T)

    def __readSlice(self, low, highs):
        if self._arc is None:
            print("arc2 is not connected")
            return

        voltage = self.readOpsWidget.readoutVoltage()
        data = self._arc().read_slice_masked(low, highs, voltage)
        bitline = self.mapper.ch2b[low]
        # convert channel order to word order
        currents = data[self.mapper.word_idxs]

        # find the non-nan indices in the current results
        idx = np.where(~np.isnan(currents))[0]
        return (voltage, currents, idx)

    def __pulseReadSlice(self, low, highs, vpulse, pulsewidth):
        if self._arc is None:
            print("arc2 is not connected")
            return

        voltage = self.readOpsWidget.readoutVoltage()
        data = self._arc().pulseread_slice_masked(low, highs, vpulse,
            int(pulsewidth*1.0e9), voltage)
        bitline = self.mapper.ch2b[low]
        # convert channel order to word order
        currents = data[self.mapper.word_idxs]

        # find the non-nan indices
        idx = np.where(~np.isnan(currents))[0]
        return (vpulse, currents, idx)

    def __finaliseOperation(self):
        if self._arc is None:
            return

        idleMode = self.arc2ConnectionWidget.idleMode
        self._arc().finalise_operation(idleMode)

    def readSelectedCell(self, cells):
        cell = cells[0]
        (w, b) = (cell.w, cell.b)
        (high, low) = self.mapper.wb2ch[w][b]
        print("read (word: %2d bit: %2d ←→ low: %2d high: %2d" % (w, b, low, high))
        if self._arc is None:
            print("arc2 is not connected")
        else:
            voltage = self.readOpsWidget.readoutVoltage()
            current = self._arc().read_one(low, high, voltage)
            self.__finaliseOperation()

            signals.valueUpdate.emit(w, b, current, voltage, 0.0, \
                self.readOpsWidget.readoutVoltage(), OpType.READ)
            signals.dataDisplayUpdate.emit(w, b)

    def readAllClicked(self):
        if self._arc is None:
            print("arc2 is not connected")
            return

        voltage = self.readOpsWidget.readoutVoltage()
        raw = self._arc().read_all(voltage, BiasOrder.Cols)
        self.__finaliseOperation()
        data = np.empty(shape=(self.mapper.nbits, self.mapper.nwords))
        for (row, channel) in enumerate(sorted(self.mapper.ch2b.keys())):
            bitline = self.mapper.ch2b[channel]
            data[bitline] = raw[row][self.mapper.word_idxs]

        shape = data.shape
        actual_voltage = np.repeat([voltage], shape[0]*shape[1]).reshape(*shape)
        self.crossbarRefresh(data, actual_voltage)

    def pulseSelectedCell(self, cells, voltage, pulsewidth):
        if self._arc is None:
            print("arc2 is not connected")
            return

        cell = cells[0]
        (w, b) = (cell.w, cell.b)
        (low, high) = self.mapper.wb2ch[w][b]

        print("Pulsing channel lowV: %d; highV: %d | V = %g; PW = %g ns" %
            (low, high, voltage, pulsewidth*1.0e9))

        self._arc().pulse_one(low, high, voltage, int(pulsewidth*1.0e9))\
                   .execute()
        signals.valueUpdate.emit(w, b, np.NaN, voltage, pulsewidth, \
            np.NaN, OpType.PULSE)
        self.__finaliseOperation()

    def pulseSelectedSlices(self, cells, voltage, pulsewidth):
        if self._arc is None:
            print("arc2 is not connected")
            return

        slices = {}

        for c in cells:
            try:
                slices[c.b].append(c.w)
            except KeyError:
                slices[c.b] = [c.w]

        for (k, v) in slices.items():
            low = self.mapper.b2ch[k]
            highs = np.array([self.mapper.w2ch[x] for x in v], dtype=np.uint64)
            print(("lowV channel: %d; highV channels:" % low), highs)
            self._arc().pulse_slice_masked(low, voltage, int(pulsewidth*1.0e9), highs)\
                       .ground_all()\
                       .execute()
            for w in idx:
                signals.valueUpdate.emit(w, k, np.NaN, voltage, pulsewidth,\
                    np.NaN, OpType.PULSE)
            self.__finaliseOperation()

    def pulseAll(self, voltage, pulsewidth):
        if self._arc is None:
            print("arc2 is not connected")
            return

        self._arc().pulse_all(voltage, int(pulsewidth*1.0e9), BiasOrder.Cols)\
                   .ground_all()\
                   .execute()
        self.__finaliseOperation()

    def addModuleClicked(self):
        mod = self.moduleListComboBox.currentData()
        self.addModuleTab(mod)

    def addModuleTab(self, kls):
        obj = kls(self._arc, self.arc2ConnectionWidget.arc2Config, \
            self.readOpsWidget.readoutVoltage(), self._datastore, \
            self.mainCrossbarWidget.selection, self.mapper)
        # update tree when experiment is finished
        obj.experimentFinished.connect(lambda w, b, path: \
            self.deviceExplorerWidget.addExperiment(w, b, path))
        wdg = QtWidgets.QWidget()
        scrollArea = QtWidgets.QScrollArea()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(obj)
        scrollArea.setLayout(layout)

        layout = QtWidgets.QVBoxLayout()
        titleLabel = QtWidgets.QLabel(obj.name)
        titleLabel.setStyleSheet('QLabel { font-weight: bold; font-size: 11pt; } ')
        layout.addWidget(titleLabel)
        layout.addWidget(QtWidgets.QLabel(obj.description))
        layout.addWidget(scrollArea)
        wdg.setLayout(layout)
        # add an attribute to quickly get to the actual module widget
        setattr(wdg, 'module', obj)
        self.experimentTabWidget.addTab(wdg, obj.name)
        # switch to the new tab
        self.experimentTabWidget.setCurrentIndex(self.experimentTabWidget.count()-1)

        if self.experimentTabWidget.count() > 0:
            self.moduleWrapStackedWidget.setCurrentIndex(0)
        else:
            self.moduleWrapStackedWidget.setCurrentIndex(1)

        self.saveModuleButton.setEnabled(True)

        return obj

    def removeCurrentModuleTab(self):
        wdg = self.experimentTabWidget.currentWidget()
        idx = self.experimentTabWidget.currentIndex()
        self.experimentTabWidget.removeTab(idx)
        wdg.setParent(None)
        del wdg

        if self.experimentTabWidget.count() > 0:
            self.moduleWrapStackedWidget.setCurrentIndex(0)
        else:
            self.moduleWrapStackedWidget.setCurrentIndex(1)

        if self.experimentTabWidget.count() == 0:
            self.saveModuleButton.setEnabled(False)

    def saveModuleClicked(self):
        wdg = self.experimentTabWidget.currentWidget()
        if wdg is None or not hasattr(wdg, 'module'):
            return

        fname = QtWidgets.QFileDialog.getSaveFileName(self, "Export Widget Data",\
            '', _MOD_FILE_FILTER)

        if fname is None or len(fname[0]) == 0:
            return

        wdg.module.exportToJson(fname[0])

    def loadModuleClicked(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, "Open Widget Data",\
            '', _MOD_FILE_FILTER)

        if fname is None or len(fname[0]) == 0:
            return

        klass = moduleClassFromJson(fname[0])

        wdg = self.addModuleTab(klass)
        wdg.loadFromJson(fname[0])


    def clearPlots(self):
        dispType = self.plottingOptionsWidget.displayType

        self.tracePlot.plot([0],[0])
        self.tracePlot.clear()
        self.pulsePlot.plot([0],[0])
        self.pulsePlot.clear()
        self.tracePlot.getAxis('left').setLabel(**dispType.plotLabel())

    def changePlotScale(self, scale):
        if scale == PlotYScale.Linear:
            self.tracePlot.setLogMode(False, False)
        elif scale == PlotYScale.Log:
            self.tracePlot.setLogMode(False, True)

    def refreshCurrentPlot(self, *args):
        cells = self.mainCrossbarWidget.selectedCells
        if len(cells) == 1:
            (w, b) = cells[0]
            self.updateSinglePlot(w, b)
        else:
            self.clearPlots()

    def valueUpdate(self, w, b, curr, volt, pw, vread, optype):
        self._datastore.update_status(w, b, curr, volt, pw, vread, optype)
        self.mainCrossbarWidget.updateData(w, b, np.abs(vread/curr))
        self.selectionChanged(self.mainCrossbarWidget.selection)

    def valueUpdateBulk(self, w, b, curr, volt, pw, vread, optype):
        self._datastore.update_status_bulk(w, b, curr, volt, pw, vread, optype)
        self.mainCrossbarWidget.updateData(w, b, np.abs(vread[-1]/curr[-1]))
        self.selectionChanged(self.mainCrossbarWidget.selection)

    def updateSinglePlot(self, w, b):

        xRange = self.plottingOptionsWidget.xRange
        dispType = self.plottingOptionsWidget.displayType

        try:
            full_timeseries = self._datastore.timeseries(w, b)
            len_timeseries = full_timeseries.shape[0]
        except KeyError: # no dataset exists
            self.clearPlots()
            return

        if xRange is None:
            timeseries = full_timeseries
            offset = 0
        else:
            timeseries = full_timeseries[-xRange:]
            offset = max(len_timeseries - xRange, 0)

        idxes = np.arange(offset, len_timeseries)

        if dispType == PlotDisplayType.Resistance:
            self.tracePlot.plot(idxes, np.abs(timeseries['read_voltage']/timeseries['current']),\
                pen={'color': '#F00', 'width': 1}, symbol='+', symbolPen=None, \
                symbolSize=6, symbolBrush='#F00',\
                clear=True)
        elif dispType == PlotDisplayType.Conductance:
            self.tracePlot.plot(idxes, np.abs(timeseries['current']/timeseries['read_voltage']),\
                pen={'color': '#F00', 'width': 1}, symbol='x', symbolPen=None, \
                symbolSize=6, symbolBrush='#F00',\
                clear=True)
        elif dispType == PlotDisplayType.Current:
            self.tracePlot.plot(idxes, timeseries['current'], \
                pen={'color': '#F00', 'width': 1}, symbol='t', symbolPen=None, \
                symbolSize=6, symbolBrush='#F00',\
                clear=True)
        elif dispType == PlotDisplayType.AbsCurrent:
            self.tracePlot.plot(idxes, np.abs(timeseries['current']), \
                pen={'color': '#F00', 'width': 1}, symbol='t1', symbolPen=None, \
                symbolSize=6, symbolBrush='#F00',\
                clear=True)
        else:
            # unknown plot type, nothing to show
            return

        self.tracePlot.getAxis('left').setLabel(**dispType.plotLabel())

        # find points with pulse operations
        idxp = np.where((timeseries['op_type'] & OpType.PULSE) == OpType.PULSE)[0]
        # find points with read operations
        idxr = np.where((timeseries['op_type'] & OpType.READ) == OpType.READ)[0]

        # plot the pulse points
        self.pulsePlot.plot(offset+idxp, timeseries['voltage'][idxp], pen=None,\
            symbolPen=None, symbolBrush=(0, 150, 150),  symbol='s',\
            symbolSize=6, clear=True )

        # this ugly hack is required because pyqtgraph has no way to plot a dataset
        # with impulses. The only way remotely resembling this setup is by using
        # this monstrosity which duplicates the indices ([2, 3, 5] → [2, 2, 3, 3, 5, 5])
        # and recreates the y-axis data with zero points in between (so for instance
        # [1e-6, 1.1e-6, 1.2e-6] → [0, 1e-6, 0, 1.1e-6, 0, 1.2e-6]). Now there are two
        # points per x-value (0.0 and the actual value). That way we can use the
        # `connect='pairs'` option of pyqtgraph to plot every other point
        # So instead of having this (default)
        #
        # |
        # |    +
        # | +  |
        # | |\ | +
        # | | \|/|
        # o-+--+-+---->
        #
        # we are getting this
        #
        # |
        # |    +
        # | +  |
        # | |  | +
        # | |  | |
        # o-+--+-+---->
        #
        # and by also omitting the symbols we finally get the impulse lines
        #
        # |
        # |
        # |    |
        # | |  |
        # | |  | |
        # o----------->

        # plot the impulse lines
        self.pulsePlot.plot(offset+np.repeat(idxp, 2), \
            np.dstack((\
                np.zeros(len(timeseries['voltage'][idxp])), timeseries['voltage'][idxp])
            ).flatten(), \
            pen=(0, 150, 150),\
            connect='pairs')

        # plot the read points
        self.pulsePlot.plot(offset+idxr, timeseries['read_voltage'][idxr], pen=None,\
            symbolPen=None, symbolBrush=(0, 0, 255),  symbol='+',\
            symbolSize=6)

    def crossbarRefresh(self, current, voltage):
        vdset = self._datastore.dataset('crossbar/voltage')
        cdset = self._datastore.dataset('crossbar/current')
        cdset[:] = current
        vdset[:] = voltage
        self.mainCrossbarWidget.setData(np.abs(vdset[:]/cdset[:]).T)

    def newDataset(self):
        if self._datastore is not None:
            # save existing data
            self._datastore.close()

            # and ask if we want to keep the temporary dataset
            if self._datastore.is_temporary:
                res = QtWidgets.QMessageBox.question(self, "Quit ArC2", \
                    "Save current dataset?")
                if res == QtWidgets.QMessageBox.StandardButton.Yes:
                    fname = QtWidgets.QFileDialog.getSaveFileName(self, \
                        "Save dataset", '', _H5_FILE_FILTER)
                    if fname is not None and len(fname[0]) > 0:
                        shutil.move(self._datastore.fname, fname[0])
                    else:
                        # if cancel is pressed, reopen the previous
                        # dataset and exit
                        fname = self._datastore.fname
                        self._datastore = H5DataStore(fname, mode=H5Mode.APPEND)
                        self._datastore.__setattr__('is_temporary', True)
                        return
                else:
                    os.remove(self._datastore.fname)

        # create a new temp dataset
        self._datastore = H5DataStore(tempfile.NamedTemporaryFile(\
            suffix='.h5', delete=False).name,\
            mode=H5Mode.WRITE)
        self._datastore.__setattr__('is_temporary', True)
        self.saveDatasetAction.setEnabled(True)
        self.saveDatasetAction.setToolTip('Save')
        self.saveDatasetAsAction.setEnabled(False)
        self.reloadFromDataset()
        self.deviceExplorerWidget.clear()
        self.deviceExplorerWidget.loadFromStore(self._datastore)

    def openDataset(self):
        if self._datastore is not None and self._datastore.is_temporary:
            self._datastore.close()

            res = QtWidgets.QMessageBox.question(self, "Quit ArC2", \
                "Save current dataset?")
            if res == QtWidgets.QMessageBox.StandardButton.Yes:
                fname = QtWidgets.QFileDialog.getSaveFileName(self, \
                    "Save dataset", '', _H5_FILE_FILTER)
                if fname is not None and len(fname[0]) > 0:
                    shutil.move(self._datastore.fname, fname[0])
                else:
                    os.remove(self._datastore.fname)
            else:
                os.remove(self._datastore.fname)

        fname = QtWidgets.QFileDialog.getOpenFileName(self, "Open dataset",\
            '', _H5_FILE_FILTER)
        if fname is not None and len(fname[0]) > 0:

            self._datastore = None
            self._datastore = H5DataStore(fname[0], mode=H5Mode.APPEND)
            self._datastore.__setattr__('is_temporary', False)
            self.saveDatasetAction.setEnabled(False)
            self.saveDatasetAction.setToolTip('Dataset is saved automatically')
            self.saveDatasetAsAction.setEnabled(True)
            self.deviceExplorerWidget.clear()
            self.deviceExplorerWidget.loadFromStore(self._datastore)
        else:
            # if no specific dataset has been opened, create a new
            # temporary one
            self._datastore = H5DataStore(tempfile.NamedTemporaryFile(\
                suffix='.h5', delete=False).name,\
                mode=H5Mode.WRITE)
            self._datastore.__setattr__('is_temporary', True)
            self.saveDatasetAction.setEnabled(True)
            self.saveDatasetAction.setToolTip('Save')
            self.saveDatasetAsAction.setEnabled(False)

        self.reloadFromDataset()

    def saveDataset(self):
        fname = QtWidgets.QFileDialog.getSaveFileName(self, "Save dataset as",\
            '', _H5_FILE_FILTER)
        if fname is not None and len(fname[0]) > 0:
            if self._datastore is None or not self._datastore.is_temporary:
                return

            self._datastore.close()
            shutil.move(self._datastore.fname, fname[0])
            self._datastore = None
            self._datastore = H5DataStore(fname[0], mode=H5Mode.APPEND)
            self._datastore.__setattr__('is_temporary', False)
            self.saveDatasetAction.setEnabled(False)
            self.saveDatasetAction.setToolTip('Dataset is saved automatically')
            self.saveDatasetAsAction.setEnabled(True)
            self.reloadFromDataset()

    def saveDatasetAs(self):
        fname = QtWidgets.QFileDialog.getSaveFileName(self, "Save dataset as",\
            '', _H5_FILE_FILTER)
        if fname is not None and len(fname[0]) > 0:
            self._datastore.close()
            if self._datastore is not None and self._datastore.is_temporary:
                shutil.move(self._datastore.fname, fname[0])
            else:
                shutil.copy2(self._datastore.fname, fname[0])

            self._datastore = None

            self._datastore = H5DataStore(fname[0], mode=H5Mode.APPEND)
            self._datastore.__setattr__('is_temporary', False)
            self.saveDatasetAction.setEnabled(False)
            self.saveDatasetAction.setToolTip('Dataset is saved automatically')
            self.reloadFromDataset()

    def reloadFromDataset(self):
        self.refreshCurrentPlot()
        vdset = self._datastore.dataset('crossbar/voltage')
        cdset = self._datastore.dataset('crossbar/current')
        self.mainCrossbarWidget.setData(np.abs(vdset[:]/cdset[:]).T)
        self.setWindowTitle('%s [%s]' % \
            (_APP_TITLE, os.path.basename(self._datastore.fname)))

    def __exportTimeSeries(self, w, b, complete):

        if complete:
            ts = self._datastore.timeseries(w, b)[0:]
        else:
            ts = self._datastore.timeseries(w, b)

            # ask for a range
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle('Export data range')
            dialog.setWindowIcon(graphics.getIcon('arc2-logo'))
            layout = QtWidgets.QGridLayout(dialog)

            layout.addWidget(QtWidgets.QLabel('From'), 0, 0)
            fromSpinBox = QtWidgets.QSpinBox(dialog)
            fromSpinBox.setMaximum(ts.shape[0])
            fromSpinBox.setMinimum(0)
            layout.addWidget(fromSpinBox, 0, 1)

            layout.addWidget(QtWidgets.QLabel('To'), 0, 2)
            toSpinBox = QtWidgets.QSpinBox(dialog)
            toSpinBox.setMaximum(ts.shape[0])
            toSpinBox.setMinimum(0)
            toSpinBox.setValue(ts.shape[0])
            layout.addWidget(toSpinBox, 0, 3)

            minButton = QtWidgets.QPushButton('Min', dialog)
            minButton.clicked.connect(lambda: fromSpinBox.setValue(0))

            maxButton = QtWidgets.QPushButton('Max', dialog)
            maxButton.clicked.connect(lambda: toSpinBox.setValue(ts.shape[0]))

            layout.addWidget(minButton, 1, 1)
            layout.addWidget(maxButton, 1, 3)

            dlgButtons = QtWidgets.QDialogButtonBox(dialog)
            dlgButtons.setStandardButtons(\
                QtWidgets.QDialogButtonBox.StandardButton.Ok | \
                QtWidgets.QDialogButtonBox.StandardButton.Cancel)

            layout.addItem(QtWidgets.QSpacerItem(20, 30, \
                QtWidgets.QSizePolicy.Policy.Fixed, \
                QtWidgets.QSizePolicy.Policy.Expanding), 2, 0)
            layout.addWidget(dlgButtons, 3, 0, 1, 4)
            dlgButtons.accepted.connect(dialog.accept)
            dlgButtons.rejected.connect(dialog.reject)

            dialog.setLayout(layout)
            if dialog.exec():
                fromIdx = fromSpinBox.value()
                toIdx = toSpinBox.value()
                if toIdx < fromIdx:
                    QtWidgets.QMessageBox.critical(self, \
                        'Export timeseries', \
                        'Export range invalid (from > to)')
                    return
                ts = ts[fromIdx:toIdx]
            else:
                return

        (fname, flt) = QtWidgets.QFileDialog.getSaveFileName(self, \
            "Export timeseries", '', _H5_TS_EXPORT_FILTER)

        if fname is None or fname == '':
            return

        if flt.endswith('(*.csv)'):
            delimiter = ','
        elif flt.endswith('(*.tsv)'):
            delimiter = '\t'
        else:
            raise ValueError('Invalid export file type')

        # ts is defined here
        np.savetxt(fname, ts, delimiter=delimiter)


    def quit(self):
        try:
            if self._arc is not None:
                self.arc2ConnectionWidget.disconnectArC2()
                self._arc = None
        except Exception:
            pass

        if self._datastore is not None:
            self._datastore.close()
            if self._datastore.is_temporary:
                res = QtWidgets.QMessageBox.question(self, "Quit ArC2", \
                    "Save current dataset?")
                if res == QtWidgets.QMessageBox.StandardButton.Yes:
                    fname = QtWidgets.QFileDialog.getSaveFileName(self, \
                        "Save dataset", '', _H5_FILE_FILTER)
                    if fname is not None and len(fname[0]) > 0:
                        shutil.move(self._datastore.fname, fname[0])
                    else:
                        os.remove(self._datastore.fname)
                else:
                    os.remove(self._datastore.fname)

    def closeEvent(self, evt):
        self.quit()
        evt.accept()
