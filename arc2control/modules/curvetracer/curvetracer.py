import numpy as np
import pyqtgraph as pg
from enum import Enum
from pyarc2 import ReadAt, ReadAfter, DataMode
from arc2control.modules.base import BaseModule, BaseOperation
from .generated.curvetracer import Ui_CurveTracerWidget
from . import MOD_NAME, MOD_TAG, MOD_DESCRIPTION
from .ct_display_widget import CTDataDisplayWidget
from arc2control import signals
from arc2control.h5utils import OpType

from PyQt6 import QtCore, QtWidgets, QtGui


_CT_DTYPE = [('voltage', '<f4'), ('current', '<f4'), ('read_voltage', '<f4')]


class BiasType(Enum):
    Staircase = 1
    Pulsed = 2


class Direction(Enum):
    V0_VP = 1
    VP_V0 = 2
    V0_VM = 3
    VM_V0 = 4
    V0_VP_V0 = 5
    VP_V0_VP = 6
    V0_VM_V0 = 7
    VM_V0_VM = 8
    V0_VP_VM_V0 = 9
    V0_VM_VP_V0 = 10
    VM_VP_V0 = 11
    VP_VM_V0 = 12


class CurveTracerOperation(BaseOperation):

    def __init__(self, params, parent):
        super().__init__(parent=parent)
        self.params = params
        self.arcconf = self.arc2Config
        self._voltages = []
        self._currents = []

    def run(self):
        if len(self.cells) != 1:
            return

        (ramps, vstep, pw, interpulse, pulses, readat, readafter, cycles) = \
            self.params
        cell = list(self.cells)[0]

        (w, b) = (cell.w, cell.b)

        for (idx, (vstart, vstop)) in enumerate(ramps):
            if vstop < vstart:
                st = -vstep
            else:
                st = vstep

            try:
                # check if the next ramp is discontinuous to this one.
                # If it is then we need to make the ramp endpoint inclusive
                # for instance if vstep=0.2 and we have two ramps from
                # 0.0 to 1.0 we want to go [0.0, 0.2, 0.4, 0.6, 0.8, 1.0] →
                # [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]. However if we have a
                # a 0.0 → 1.0 → 0.0 it means the actual ramps should be
                # [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 0.8, 0.6, 0.4, 0.2, 0.0] and
                # NOT
                # [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.0, 0.8, 0.6, 0.4, 0.2, 0.0] and
                #                           ^^^^^^^^
                #                           ||||||||
                #                there should be only one value at the
                #                apex of the ramp (or at the nadir
                #                if it's a 1.0 → 0.0 → 1.0 ramp)
                (next_vstart, next_vstop) = ramps[idx+1]
                if vstop != next_vstart:
                    endpoint_inclusive = True
                else:
                    endpoint_inclusive = False
            except IndexError:
                # irrelevant: it means we are on the last ramp anyway
                pass

            if idx == len(ramps) - 1 or endpoint_inclusive:
                (v, i) = self.do_ramp(w, b, vstart, st, vstop+st/2, pw, \
                    interpulse, pulses, readat, readafter)
            else:
                (v, i) = self.do_ramp(w, b, vstart, st, vstop-st/2, pw, \
                    interpulse, pulses, readat, readafter)

            self._voltages.extend(v)
            self._currents.extend(i)

        self.finished.emit()


    def do_ramp(self, w, b, vstart, vstep, vstop, pw, interpulse, pulses, readat, readafter):

        # convert pulse width and interpulses to ns
        pw = int(pw*1e9)
        interpulse = int(interpulse * 1e9)
        (high, low) = self.mapper.wb2ch[w][b]

        # ensure we are not tied to a hard GND first
        self.arc.connect_to_gnd(np.array([], dtype=np.uint64))

        self.arc.generate_ramp(high, low, vstart, vstep, vstop, pw, interpulse,
            pulses, readat, readafter)

        voltages = np.arange(vstart, vstop+vstep/2.0, vstep)\
                     .repeat(np.max((pulses, 1)))
        #print(voltages)

        self.arc.execute()
        self.arc.finalise_operation(self.arcconf.idleMode)
        currents = np.empty(shape=voltages.shape)
        for (i, (v, d)) in enumerate(zip(voltages, self.arc.get_iter(DataMode.Bits))):
            curr = d[0][self.mapper.bit_idxs][b]
            currents[i] = curr

        return (voltages, currents)

    def curveData(self):
        readat = self.params[5]
        cycles = self.params[6]
        return (np.array(self._voltages), -np.array(self._currents), readat, cycles)


class CurveTracer(BaseModule, Ui_CurveTracerWidget):

    def __init__(self, arc, arcconf, vread, store, cells, mapper, parent=None):

        Ui_CurveTracerWidget.__init__(self)
        BaseModule.__init__(self, arc, arcconf, vread, store, \
            MOD_NAME, MOD_TAG, cells, mapper, parent=parent)
        self._thread = None

        self.setupUi(self)
        self.rampInterDurationWidget.setEnabled(False)
        self.__populateIVTypeComboBox()
        self.__populateBiasTypeComboBox()
        self.__populateReadAtComboBox()

        self.rampSelectedButton.clicked.connect(self.rampSelectedClicked)
        self.rampSelectedButton.setEnabled((len(self.cells) == 1) and (self.arc is not None))
        self.biasTypeComboBox.currentIndexChanged.connect(self.biasTypeChanged)
        signals.crossbarSelectionChanged.connect(self.crossbarSelectionChanged)
        signals.arc2ConnectionChanged.connect(self.crossbarSelectionChanged)
        signals.readoutVoltageChanged.connect(self.readoutVoltageChanged)

    def __populateIVTypeComboBox(self, setFont=True):
        box = self.ivTypeComboBox
        if setFont:
            font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
            font.setPointSize(9)
            box.setFont(font)
        box.addItem('V₀❯V+❯V–❯V₀', Direction.V0_VP_VM_V0)
        box.addItem('V₀❯V–❯V+❯V₀', Direction.V0_VM_VP_V0)
        box.insertSeparator(box.count())
        box.addItem('V₀❯V+❯V₀', Direction.V0_VP_V0)
        box.addItem('V+❯V₀❯V+', Direction.VP_V0_VP)
        box.addItem('V₀❯V–❯V₀', Direction.V0_VM_V0)
        box.addItem('V–❯V₀❯V–', Direction.VM_V0_VM)
        box.insertSeparator(box.count())
        box.addItem('V₀❯V+', Direction.V0_VP)
        box.addItem('V+❯V₀', Direction.VP_V0)
        box.addItem('V₀❯V–', Direction.V0_VM)
        box.addItem('V–❯V₀', Direction.VM_V0)

    @property
    def description(self):
        return MOD_DESCRIPTION

    def __populateBiasTypeComboBox(self):
        box = self.biasTypeComboBox
        box.addItem('Staircase', BiasType.Staircase)
        box.addItem('Pulsed', BiasType.Pulsed)

    def __populateReadAtComboBox(self):
        box = self.readAtComboBox
        box.addItem('Bias', ReadAt.Bias)
        box.addItem('Vread (%.2f V)' % self.readoutVoltage, \
            ReadAt.Arb(self.readoutVoltage))

    def __makeRampStops(self):

        def fix_stops(stops, step):
            actual_stops = []

            previous = None
            current = None

            for (l, h) in stops:
                if current is None:
                    current = (l, h)
                else:
                    previous = current
                    current = (l, h)

                if previous is None:
                    actual_stops.append((l, h))
                    continue

                (curr_l, curr_h) = current
                (prev_l, prev_h) = previous

                if prev_h < prev_l:
                    step = -step

                # there's a gap between current low and previous
                # high, so ensure that the previous low is actually
                # inclusive
                if curr_l != prev_h:
                    actual_stops[-1] = (prev_l, prev_h + step/2)
                actual_stops.append((l, h))

            return actual_stops

        direction = self.ivTypeComboBox.currentData()
        step = np.abs(self.rampVStepSpinBox.value())
        vo = np.abs(self.rampVStartSpinBox.value())
        vp = np.abs(self.rampVPosMaxSpinBox.value())
        vm = -np.abs(self.rampVNegMaxSpinBox.value())
        cycles = self.rampCyclesSpinBox.value()

        should_fix = True

        if direction == Direction.V0_VP_VM_V0:
            stops = [(vo, vp), (vp, vo), (-vo, vm), (vm, -vo)]
        elif direction == Direction.V0_VM_VP_V0:
            stops = [(-vo, vm), (vm, -vo), (vo, vp), (vp, vo)]
        elif direction == Direction.VP_VM_V0:
            stops = [(vp, vo), (-vo, vm), (vm, -vo)]
        elif direction == Direction.VM_VP_V0:
            stops = [(vm, -vo), (vo, vp), (vp, vo)]
        elif direction == Direction.V0_VP_V0:
            stops = [(vo, vp), (vp, vo)]
        elif direction == Direction.VP_V0_VP:
            stops = [(vp, vo), (vo, vp)]
        elif direction == Direction.V0_VM_V0:
            stops = [(-vo, vm), (vm, -vo)]
        elif direction == Direction.VM_V0_VM:
            stops = [(vm, -vo), (-vo, vm)]
        elif direction == Direction.V0_VP:
            stops = [(vo, vp)]
            should_fix = False
        elif direction == Direction.VP_V0:
            stops = [(vp, vo)]
            should_fix = False
        elif direction == Direction.V0_VM:
            stops = [(-vo, vm)]
            should_fix = False
        elif direction == Direction.VM_V0:
            stops = [(vm, -vo)]
            should_fix = False
        else:
            raise ValueError("Unknown ramp direction:", direction)

        # if we are doing multi-direction ramp pulses must be fixed
        # to avoid duplicate data
        # the `* cycles` part will repeat the ramp before fixing it
        if should_fix:
            return fix_stops(stops * cycles, step)
        else:
            return stops * cycles

    def crossbarSelectionChanged(self, cells):
        self.rampSelectedButton.setEnabled((len(self.cells) == 1) and (self.arc is not None))

    def rampSelectedClicked(self):
        self._thread = CurveTracerOperation(self.__rampParams(), self)
        self._thread.finished.connect(self.__threadFinished)
        self._thread.start()

    def readoutVoltageChanged(self):
        idx = self.readAtComboBox.currentIndex()
        self.readAtComboBox.clear()
        self.__populateReadAtComboBox()
        self.readAtComboBox.setCurrentIndex(idx)

    def biasTypeChanged(self, idx):
        biasType = self.biasTypeComboBox.itemData(idx)
        self.rampInterDurationWidget.setEnabled(biasType != BiasType.Staircase)

    def loadFromJson(self, fname):
        super().loadFromJson(fname)
        self.rampInterDurationWidget.setEnabled(self.biasTypeComboBox.currentIndex() == 1)

    def __rampParams(self):
        vstep = self.rampVStepSpinBox.value()
        pulses = self.rampPulsesSpinBox.value()
        pw = self.rampPwDurationWidget.getDuration()
        readat = self.readAtComboBox.currentData()
        cycles = self.rampCyclesSpinBox.value()
        if self.biasTypeComboBox.currentData() == BiasType.Staircase:
            inter = 0
        else:
            inter = self.rampInterDurationWidget.getDuration()

        ramps = self.__makeRampStops()
        return (ramps, vstep, pw, inter, pulses, readat, ReadAfter.Pulse, cycles)

    def __threadFinished(self):
        self._thread.wait()
        self._thread.setParent(None)
        data = self._thread.curveData()
        (ramp, vstep, pw, inter, pulses, _, readafter, cycles) = \
            self._thread.params
        self._thread = None
        (w, b) = list(self.cells)[0]
        dset = self.datastore.make_wb_table(w, b, MOD_TAG, (len(data[0]), ), _CT_DTYPE)
        dset[:, 'voltage'] = data[0]
        dset[:, 'current'] = data[1]

        vread_raw = data[2]
        if vread_raw == ReadAt.Bias:
            vread = data[0]
        else:
            vread = np.array([vread_raw.voltage()]).repeat(len(data[0]))

        dset[:, 'read_voltage'] = vread

        dset.attrs['ramp'] = ramp
        dset.attrs['vstep'] = vstep
        dset.attrs['pw'] = pw
        dset.attrs['inter'] = inter
        dset.attrs['pulses'] = pulses
        dset.attrs['cycles'] = cycles
        dset.attrs['read_after'] = str(readafter)

        pw = np.array([self.__rampParams()[3]]).repeat(len(data[0]))
        optypes = np.array([OpType.PULSEREAD]).repeat(len(data[0]))
        signals.valueBulkUpdate.emit(w, b, data[1], data[0], pw, vread, optypes)
        signals.dataDisplayUpdate.emit(w, b)
        self.experimentFinished.emit(w, b, dset.name)

    @staticmethod
    def display(dataset):
        return CTDataDisplayWidget(dataset)
