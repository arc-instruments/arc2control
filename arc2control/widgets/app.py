import PyQt6
from PyQt6 import QtCore, QtWidgets
from .generated.mainwindow import Ui_ArC2MainWindow

import sys
import time
import os.path
import numpy as np
from functools import partial
import pyqtgraph as pg
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

from pyarc2 import Instrument, BiasOrder, ControlMode, ReadAt, \
    ReadAfter, DataMode
from .common import Polarity
from .arc2connection_widget import ArC2IdleMode, ArC2ControlMode, \
    ArC2ConnectionWidget
from .readops_widget import ReadOpsWidget
from .rampops_widget import RampOpsWidget
from .pulseops_widget import PulseOpsWidget
from .plottingoptions_widget import DisplayType as PlotDisplayType
from .plottingoptions_widget import PlottingOptionsWidget
from .. import graphics
import weakref


class App(Ui_ArC2MainWindow, QtWidgets.QMainWindow):

    def __init__(self, mapping, parent=None):
        self._arc = None
        self.mapper = mapping
        Ui_ArC2MainWindow.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setupUi(self)
        self._setupControlWidgets()
        self._setupPlottingWidgets()

        shape = self.mainCrossbarWidget.size
        data = np.zeros((32, 32))
        data[:] = np.NaN
        self.mainCrossbarWidget.setData(data)

        self.rampOpsWidget = self.addExperimentTab(RampOpsWidget, "Ramping")

        self._connectSignals()

        self.setWindowTitle("ArC2 Control Panel")
        self.setWindowIcon(graphics.getIcon('arc2-logo'))
        self.resize(950, 800)

        self.show()

    def _connectSignals(self):

        self.selectAllButton.clicked.connect(lambda: self.mainCrossbarWidget.selectAll())

        self.mainCrossbarWidget.selectionChanged.connect(self.selectionChanged)
        self.mainCrossbarWidget.mousePositionChanged.connect(self.mousePositionChanged)
        self.readOpsWidget.readSelectedClicked.connect(self.readSelectedClicked)
        self.readOpsWidget.readAllClicked.connect(self.readAllClicked)
        self.arc2ConnectionWidget.connectionChanged.connect(self.connectionChanged)

        self.pulseOpsWidget.positivePulseClicked.connect(\
            partial(self.pulseSelectedClicked, polarity=Polarity.POSITIVE))
        self.pulseOpsWidget.negativePulseClicked.connect(\
            partial(self.pulseSelectedClicked, polarity=Polarity.NEGATIVE))
        self.pulseOpsWidget.positivePulseReadClicked.connect(\
            partial(self.pulseReadSelectedClicked, polarity=Polarity.POSITIVE))
        self.pulseOpsWidget.negativePulseReadClicked.connect(\
            partial(self.pulseReadSelectedClicked, polarity=Polarity.POSITIVE))

        self.rampOpsWidget.rampSelectedClicked.connect(self.rampSelectedClicked)
        self.selectionChanged()

    def _setupControlWidgets(self):
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

    def _setupPlottingWidgets(self):
        self.tracePlot = self.mainPlotWidget.addPlot(name='trace')
        self.tracePlot.getAxis('left').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.tracePlot.getAxis('right').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.mainPlotWidget.nextRow()
        self.pulsePlot = self.mainPlotWidget.addPlot(name='pulse')
        self.pulsePlot.getAxis('left').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.pulsePlot.getAxis('right').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.pulsePlot.setXLink('trace')
        self.mainPlotWidget.ci.layout.setRowStretchFactor(0, 2)
        self.mainPlotWidget.ci.layout.setRowStretchFactor(1, 1)

    def connectionChanged(self, connected):
        if connected:
            self._arc = weakref.ref(self.arc2ConnectionWidget.arc2)
            pass
        else:
            self._arc = None

    def selectionChanged(self):
        cells = self.mainCrossbarWidget.selectedCells

        if len(cells) == 0:
            self.readOpsWidget.setReadSelectedEnabled(False)
            self.pulseOpsWidget.setPulseEnabled(Polarity.POSITIVE, False)
            self.pulseOpsWidget.setPulseEnabled(Polarity.NEGATIVE, False)
            self.pulseOpsWidget.setPulseReadEnabled(Polarity.POSITIVE, False)
            self.pulseOpsWidget.setPulseReadEnabled(Polarity.NEGATIVE, False)
            self.rampOpsWidget.setRampEnabled(False)
        else:
            self.readOpsWidget.setReadSelectedEnabled(True)
            self.pulseOpsWidget.setPulseEnabled(Polarity.POSITIVE, True)
            self.pulseOpsWidget.setPulseEnabled(Polarity.NEGATIVE, True)
            self.pulseOpsWidget.setPulseReadEnabled(Polarity.POSITIVE, True)
            self.pulseOpsWidget.setPulseReadEnabled(Polarity.NEGATIVE, True)
            self.rampOpsWidget.setRampEnabled(len(cells) == 1)

        if len(cells) != 1:
            return
        else:
            cell = cells[0]
            value = self.mainCrossbarWidget.valueOf(cell)
            self.readOpsWidget.setValue(cell.w, cell.b, value, suffix='Ω')

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

    def readSelectedClicked(self):
        cells = self.mainCrossbarWidget.selectedCells
        if len(cells) != 1:
            self.readSelectedSlices(cells)
        else:
            self.readSelectedCell(cells)

    def _pulseOpInner(self, voltage, pulsewidth, _single, _slice, _all):
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

        self._pulseOpInner(v, pw, _single, _slice, _all)

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

        self._pulseOpInner(v, pw, _single, _slice, _all)

    def pulseReadSelectedCell(self, cells, vpulse, pulsewidth, vread):
        cell = cells[0]
        (w, b) = (cell.w, cell.b)
        (low, high) = self.mapper.wb2ch[w][b]
        print("pulseread (word: %2d bit: %2d ←→ low: %2d high: %2d)" % (w, b, low, high))
        print("pulseread (V = %g, PW = %g ns)" % (vpulse, pulsewidth*1.0e9))
        if self._arc is None:
            print("arc2 is not connected")
        else:
            voltage = self.readOpsWidget.readoutVoltage()
            current = self._arc().pulseread_one(low, high, vpulse, int(pulsewidth*1.0e9),
                vread)
            self._finaliseOperation()
            self.mainCrossbarWidget.updateData(w, b, voltage/abs(current))
            self.readOpsWidget.setValue(w, b, voltage/abs(current))
        self.selectionChanged()

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
                (res, idx) = self._pulseReadSlice(self.mapper.b2ch[k],
                    np.array([self.mapper.w2ch[x] for x in v], dtype=np.uint64),
                    vpulse, pulsewidth)
                data[k][idx] = res[idx]
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
        self._finaliseOperation()
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
                (res, idx) = self._readSlice(self.mapper.b2ch[k],
                    np.array([self.mapper.w2ch[x] for x in v], dtype=np.uint64))
                data[k][idx] = res[idx]
            except TypeError:
                # arc not connected
                return

        self.mainCrossbarWidget.setData(data.T)

    def rampSelectedClicked(self):

        if self._arc is None:
            return

        cell = self.mainCrossbarWidget.selectedCells[0]

        (vstart, vstep, vstop, pw, interpulse, pulses) = \
            self.rampOpsWidget.rampParams()

        # in nanoseconds
        pw = int(pw * 1e9)
        # in nanoseconds
        interpulse = int(interpulse * 1e9)

        (w, b) = (cell.w, cell.b)
        (low, high) = self.mapper.wb2ch[w][b]

        print("W: %02d B: %02d (low: %02d high: %02d); Vstart: %.2f V Vstep: %.2f V "
            "Vend: %.2f; PW: %d ns I: %d ns N: %d"
            % (w, b, low, high, vstart, vstep, vstop, pw, interpulse, pulses))

        self._arc().generate_ramp(low, high, vstart, vstep, vstop, pw, interpulse,
            pulses, ReadAt.Bias, ReadAfter.Pulse)
        if vstop < vstart:
            voltages = np.arange(vstop-vstep/2.0, vstart, vstep)\
                         .repeat(np.max((pulses, 1)))
        else:
            voltages = np.arange(vstart, vstop+vstep/2.0, vstep)\
                         .repeat(np.max((pulses, 1)))

        self._arc().execute()
        self._finaliseOperation()
        self._arc().wait()
        currents = np.empty(shape=voltages.shape)
        for (i, (v, d)) in enumerate(zip(voltages, self._arc().get_iter(DataMode.Bits))):
            curr = d[0][self.mapper.bit_idxs][b]
            if v != 0.0:
                print("V = %.2f V; I = %.2e A; R = %s" % (v, curr,
                    pg.siFormat(np.abs(v/curr), suffix='Ω')))
            else:
                print("V = %.2f V; I = %.2e A; R = N/A" % (v, curr))
            currents[i] = curr
        print("===")
        if self.rampOpsWidget.showResultChecked():
            self._plotData(voltages, currents, 'Voltage', 'Current',
                xunit='V', yunit='A')

    def _readSlice(self, low, highs):
        if self._arc is None:
            print("arc2 is not connected")
            return

        voltage = self.readOpsWidget.readoutVoltage()
        data = self._arc().read_slice_masked(low, highs, voltage)
        bitline = self.mapper.ch2b[low]
        # convert channel order to word order
        data = voltage/abs(data[self.mapper.word_idxs])

        # find the non-nan indices
        idx = np.where(~np.isnan(data))[0]
        return (data, idx)

    def _pulseReadSlice(self, low, highs, vpulse, pulsewidth):
        if self._arc is None:
            print("arc2 is not connected")
            return

        voltage = self.readOpsWidget.readoutVoltage()
        data = self._arc().pulseread_slice_masked(low, highs, vpulse,
            int(pulsewidth*1.0e9), voltage)
        bitline = self.mapper.ch2b[low]
        # convert channel order to word order
        data = voltage/abs(data[self.mapper.word_idxs])

        # find the non-nan indices
        idx = np.where(~np.isnan(data))[0]
        return (data, idx)

    def _finaliseOperation(self):
        if self._arc is None:
            return

        if self.arc2ConnectionWidget.idleMode == ArC2IdleMode.Float:
            self._arc().ground_all_fast().float_all().execute()
        elif self.arc2ConnectionWidget.idleMode == ArC2IdleMode.Gnd:
            self._arc().ground_all().execute()

    def readSelectedCell(self, cells):
        cell = cells[0]
        (w, b) = (cell.w, cell.b)
        (low, high) = self.mapper.wb2ch[w][b]
        print("read (word: %2d bit: %2d ←→ low: %2d high: %2d" % (w, b, low, high))
        if self._arc is None:
            print("arc2 is not connected")
        else:
            voltage = self.readOpsWidget.readoutVoltage()
            current = self._arc().read_one(low, high, voltage)
            self._finaliseOperation()
            self.mainCrossbarWidget.updateData(w, b, voltage/abs(current))

            self._dataset.update_status(w, b, current, voltage, 0.0,
                self.readOpsWidget.readoutVoltage(), OpType.READ)
            timeseries = self._dataset.timeseries(w, b)[:100]
            self.tracePlot.plot(np.abs(timeseries['voltage']/timeseries['current']),\
                clear=True)
            self.pulsePlot.plot(timeseries['voltage'], pen=None,\
                symbolPen=None, symbolBrush=(0, 0, 255),  symbol='+',\
                symbolSize=6, clear=True)

        self.selectionChanged()

    def readAllClicked(self):
        if self._arc is None:
            print("arc2 is not connected")
            return

        voltage = self.readOpsWidget.readoutVoltage()
        raw = self._arc().read_all(voltage, BiasOrder.Cols)
        self._finaliseOperation()
        data = np.empty(shape=(self.mapper.nbits, self.mapper.nwords))
        for (row, channel) in enumerate(sorted(self.mapper.ch2b.keys())):
            bitline = self.mapper.ch2b[channel]
            data[bitline] = voltage/np.abs(raw[row][self.mapper.word_idxs])

        self.mainCrossbarWidget.setData(data.T)

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
        self._finaliseOperation()

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
            self._finaliseOperation()

    def pulseAll(self, voltage, pulsewidth):
        if self._arc is None:
            print("arc2 is not connected")
            return

        self._arc().pulse_all(voltage, int(pulsewidth*1.0e9), BiasOrder.Cols)\
                   .ground_all()\
                   .execute()
        self._finaliseOperation()

    def _plotData(self, x, y, xlabel, ylabel, xunit=None, yunit=None, logscale=False):
        dialog = QtWidgets.QDialog(self)
        box = QtWidgets.QHBoxLayout()
        dialog.setWindowTitle("Ramp results")

        gv = pg.GraphicsLayoutWidget()
        plot = gv.addPlot()
        plot.plot(x, y, pen=None, symbol='+')
        plot.getAxis('bottom').setLabel(xlabel, units=xunit)
        plot.getAxis('left').setLabel(ylabel, units=yunit)

        box.addWidget(gv)
        dialog.setLayout(box)

        dialog.show()

    def addExperimentTab(self, kls, title):
        obj = kls()
        wdg = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(obj)
        #layout.addItem(QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Policy.Fixed,\
        #    QtWidgets.QSizePolicy.Policy.Expanding))
        #layout.setStretch(1,1)
        wdg.setLayout(layout)
        self.experimentTabWidget.addTab(wdg, title)

        return obj

    def closeEvent(self, evt):
        try:
            if self._arc is not None:
                self.arc2ConnectionWidget.disconnectArC2()
                self._arc = None
        except Exception:
            pass

        if self._dataset is not None:
            self._dataset.close()
            res = QtWidgets.QMessageBox.question(self, "Quit ArC2", "Delete temporary dataset?")
            if res == QtWidgets.QMessageBox.StandardButton.Yes:
                os.remove(self._dataset.fname)

        evt.accept()
