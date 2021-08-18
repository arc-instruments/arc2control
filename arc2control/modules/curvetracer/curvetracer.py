import numpy as np
import pyqtgraph as pg
from pyarc2 import ReadAt, ReadAfter, DataMode
from arc2control.modules.base import BaseModule, BaseOperation
from .generated.curvetracer import Ui_CurveTracerWidget
from . import MOD_NAME, MOD_TAG
from arc2control import signals

from PyQt6 import QtWidgets


class CurveTracerOperation(BaseOperation):

    def __init__(self, params, parent):
        super().__init__(parent=parent)
        self.params = params
        self.arcconf = self.arc2Config
        self._data = None

    def run(self):
        if len(self.cells) != 1:
            return

        (vstart, vstep, vstop, pw, interpulse, pulses) = self.params
        cell = list(self.cells)[0]

        pw = int(pw*1e9)
        interpulse = int(interpulse * 1e9)
        (w, b) = (cell.w, cell.b)
        (low, high) = self.parent.mapper.wb2ch[w][b]

        print("W: %02d B: %02d (low: %02d high: %02d); Vstart: %.2f V Vstep: %.2f V "
            "Vend: %.2f; PW: %d ns I: %d ns N: %d"
            % (w, b, low, high, vstart, vstep, vstop, pw, interpulse, pulses))

        self.arc.generate_ramp(low, high, vstart, vstep, vstop, pw, interpulse,
            pulses, ReadAt.Bias, ReadAfter.Pulse)

        if vstop < vstart:
            voltages = np.arange(vstop-vstep/2.0, vstart, vstep)\
                         .repeat(np.max((pulses, 1)))
        else:
            voltages = np.arange(vstart, vstop+vstep/2.0, vstep)\
                         .repeat(np.max((pulses, 1)))

        self.arc.execute()
        self.arc.finalise_operation(self.arcconf.idleMode)
        self.arc.wait()
        currents = np.empty(shape=voltages.shape)
        for (i, (v, d)) in enumerate(zip(voltages, self.arc.get_iter(DataMode.Bits))):
            curr = d[0][self.mapper.bit_idxs][b]
            if v != 0.0:
                print("V = %.2f V; I = %.2e A; R = %s" % (v, curr,
                    pg.siFormat(np.abs(v/curr), suffix='Ω')))
            else:
                print("V = %.2f V; I = %.2e A; R = N/A" % (v, curr))
            currents[i] = curr
        print("===")
        self._data = (voltages, currents)
        self.finished.emit()

    @property
    def data(self):
        return self._data


class CurveTracer(BaseModule, Ui_CurveTracerWidget):

    def __init__(self, arc, arcconf, vread, store, cells, mapper, parent=None):

        Ui_CurveTracerWidget.__init__(self)
        BaseModule.__init__(self, arc, arcconf, vread, store, \
            MOD_NAME, MOD_TAG, cells, mapper, parent=parent)
        self._thread = None

        self.setupUi(self)

        self.rampSelectedButton.clicked.connect(self.rampSelectedClicked)
        self.rampSelectedButton.setEnabled((len(self.cells) == 1) and (self.arc is not None))
        signals.crossbarSelectionChanged.connect(self.crossbarSelectionChanged)
        signals.arc2ConnectionChanged.connect(self.crossbarSelectionChanged)

    def crossbarSelectionChanged(self, cells):
        self.rampSelectedButton.setEnabled((len(self.cells) == 1) and (self.arc is not None))

    def rampSelectedClicked(self):
        self._thread = CurveTracerOperation(self._rampParams(), self)
        self._thread.finished.connect(self._threadFinished)
        self._thread.start()

    def _rampParams(self):
        vstart = self.rampVStartSpinBox.value()
        vstep = self.rampVStepSpinBox.value()
        vstop = self.rampVStopSpinBox.value()
        pulses = self.rampPulsesSpinBox.value()
        pw = self.rampPwDurationWidget.getDuration()
        inter = self.rampInterDurationWidget.getDuration()

        return (vstart, vstep, vstop, pw, inter, pulses)

    def _threadFinished(self):
        self._thread.wait()
        self._thread.setParent(None)
        data = self._thread.data
        self._thread = None
        print("curve tracer finished")
        self._plotData(data[0], data[1], "Voltage", "Current", 'V', 'A')

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

