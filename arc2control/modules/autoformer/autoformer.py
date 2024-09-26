import numpy as np
import pyqtgraph as pg
from enum import Enum
from pyarc2 import ReadAt
from arc2control.modules import _uisFromModuleResources
from arc2control.modules.base import BaseModule, BaseOperation, modaction
from . import MOD_NAME, MOD_TAG, MOD_DESCRIPTION
from .af_display_widget import AFDataDisplayWidget
from arc2control import signals
from arc2control.h5utils import OpType


GeneratedElements = _uisFromModuleResources(__name__.rpartition('.')[0]+".uis")


_AF_DTYPE = [('voltage', '<f4'), ('current', '<f4'), ('read_voltage', '<f4'), ('pulse_width', '<f4')]


class PulseType(Enum):
    Diff = 1
    Single = 2

class Polarity(Enum):
    Pos = 1
    Neg = 2

class SweepType(Enum):
    Geo = 1
    Lin = 2

class AutoFormerOperation(BaseOperation):

    def __init__(self, params, parent):
        super().__init__(parent=parent)
        self.params = params
        self.arcconf = self.arc2Config
        self._voltages = []
        self._currents = []
        self._pws = []

    def run(self):
        if len(self.cells) != 1:
            return

        (vstart, vstep, vlim, pwstart, pwlimit, pulsetype, polarity, pulses, readat, rtarget, \
            pwsweeptype, pwintervals, dopwsweep, dovsweep, doreset, dofullreset, resetstep, deltar) = self.params
        cell = list(self.cells)[0]

        (w, b) = (cell.w, cell.b)
        finished = False
        reset = False
        vrampstart = vstart
        while finished == False:
            if reset == True and doreset == True and dofullreset == False:
                vrampstart = max(self._voltages[-1] - resetstep, vstart)
            if polarity == Polarity.Pos:
                (v, i, s, finished, reset) = self.do_form(w, b, vrampstart, vstep, vlim, pwstart, \
                    pwlimit, pulsetype, polarity, pulses, readat, rtarget, \
                    pwsweeptype, pwintervals, dopwsweep, dovsweep, doreset, deltar)
            else:
                (v, i, s, finished, reset) = self.do_form(w, b, -vrampstart, -vstep, -vlim, pwstart, \
                    pwlimit, pulsetype, polarity, pulses, readat, rtarget, \
                pwsweeptype, pwintervals, dopwsweep, dovsweep, doreset, deltar)
            self._voltages.extend(v)
            self._currents.extend(i)
            self._pws.extend(s)

        self.operationFinished.emit()


    def do_form(self, w, b, vstart, vstep, vlim, pwstart, pwlimit, pulsetype, polarity, pulses, \
            readat, rtarget, pwsweeptype, pwintervals, dopwsweep, dovsweep, doreset, deltar):

        # convert pulse width and interpulses to ns
        (high, low) = self.mapper.wb2ch[w][b]
        pwstart = np.rint(pwstart*1e9)
        pwlimit = np.rint(pwlimit*1e9)
        curr = np.empty(64)
        i = 0

        if dopwsweep and pwsweeptype == SweepType.Lin:
            pwsweep = np.linspace(pwstart, pwlimit, np.max((pwintervals, 1)))
        elif dopwsweep and pwsweeptype == SweepType.Geo:
            pwsweep = np.geomspace(pwstart, pwlimit, np.max((pwintervals, 1)))
        else:
            pwsweep = np.array([pwstart])

        if dovsweep:
            vsweep = np.arange(vstart, vlim+vstep/2.0, vstep)
        else:
            vsweep = np.array([vstart])

        pwshort = np.repeat(pwsweep, (np.max((pulses, 1))))
        pulsewidths = np.tile(pwshort, (np.max((pulses, 1))*len(vsweep))).astype(int)
        pws = np.tile((pwshort*1e-9), (np.max((pulses, 1))*len(vsweep)))
        voltages = np.repeat(vsweep, (np.max((pulses, 1))*len(pwsweep)))
        currents = np.empty(shape=voltages.shape)

        # ensure we are not tied to a hard GND first
        self.arc.connect_to_gnd(np.array([], dtype=np.uint64))

        rlast = abs(readat/self.arc.read_one(low, high, readat))
        rtrip = rlast - (rlast * 0.01 * deltar)
        trip = False

        while i < len(voltages) and rlast > rtarget and trip == False:
            timing_array = [None, None, None, None, None, None, None, None]
            timing_array[np.floor(low/8).astype(int)] = pulsewidths[i]
            if pulsetype == PulseType.Diff:
                currents[i] = self.arc.pulseread_one(low, high, voltages[i], pulsewidths[i], readat)
            elif pulsewidths[i] <= 500e6:
                self.arc.config_channels([(high, 0), (low, 0)], None)
                self.arc.pulse_slice_fast_open([(low, -voltages[i], 0)], timing_array, True)
                self.arc.delay(pulsewidths[i])
                self.arc.config_channels([(high, 0), (low, -readat)], None)
                currents[i] = self.arc.read_slice_open([high], True)[high]
            else:
                self.arc.config_channels([(high, 0), (low, -voltages[i])], None)
                self.arc.delay(pulsewidths[i])
                self.arc.config_channels([(high, 0), (low, 0)], None)
                self.arc.config_channels([(high, 0), (low, -readat)], None)
                currents[i] = self.arc.read_slice_open([high], True)[high]

            rlast = abs(readat/currents[i])

            if rlast < rtrip and doreset == True:
                trip = True
            i = i + 1

        self.arc.execute()
        self.arc.finalise_operation(self.arcconf.idleMode)

        if rlast < rtarget or i >= len(voltages):
            finished = True
        else:
            finished = False

        voltages = np.resize(voltages, (i,))
        currents = np.resize(currents, (i,))
        pws = np.resize(pws, (i,))

        return (voltages, currents, pws, finished, trip)

    def formData(self):
        readat = self.params[8]
        return (np.array(self._voltages), -np.array(self._currents), np.array(self._pws))


class AutoFormer(BaseModule, GeneratedElements.Ui_AutoFormerWidget):

    def __init__(self, arc, arcconf, vread, store, cells, mapper, parent=None):

        GeneratedElements.Ui_AutoFormerWidget.__init__(self)
        BaseModule.__init__(self, arc, arcconf, vread, store, \
            MOD_NAME, MOD_TAG, cells, mapper, parent=parent)
        self._thread = None

        self.setupUi(self)

        self.__populatePolarityComboBox()
        self.__populatePulseTypeComboBox()
        self.__populateReadAtComboBox()
        self.__populatepwSweepComboBox()

        self.vSweepCheckBox.setChecked(True)
        self.vSweepCheckBox.toggled.connect(\
            lambda checked: self.rampVLimSpinBox.setEnabled(checked))
        self.vSweepCheckBox.toggled.connect(\
            lambda checked: self.rampVStepSpinBox.setEnabled(checked))
        self.rampVStartSpinBox.valueChanged.connect(self.updateVLim)
        self.rampVLimSpinBox.valueChanged.connect(self.updateVLim)

        self.pwSweepCheckBox.setChecked(False)
        self.pwSweepCheckBox.toggled.connect(\
            lambda checked: self.pwLimitWidget.setEnabled(checked))
        self.pwSweepCheckBox.toggled.connect(\
            lambda checked: self.pwSweepComboBox.setEnabled(checked))
        self.pwSweepCheckBox.toggled.connect(\
            lambda checked: self.intervalsSpinBox.setEnabled(checked))
        self.pwLimitWidget.setEnabled(False)
        self.pwSweepComboBox.setEnabled(False)
        self.intervalsSpinBox.setEnabled(False)

        self.resetCheckBox.toggled.connect(\
            lambda checked: self.rampResetSpinBox.setEnabled(checked))
        self.resetCheckBox.toggled.connect(\
            lambda checked: self.fullResetCheckBox.setEnabled(checked))
        self.resetCheckBox.toggled.connect(self.updateResetUI)
        self.fullResetCheckBox.toggled.connect(self.updateResetUI)
        self.rampResetSpinBox.setEnabled(False)
        self.fullResetCheckBox.setEnabled(False)
        self.resetStepSpinBox.setEnabled(False)

        self.generateEstimate()
        self.rampVStartSpinBox.valueChanged.connect(self.generateEstimate)
        self.rampVLimSpinBox.valueChanged.connect(self.generateEstimate)
        self.rampVStepSpinBox.valueChanged.connect(self.generateEstimate)
        self.rampPulsesSpinBox.valueChanged.connect(self.generateEstimate)
        self.intervalsSpinBox.valueChanged.connect(self.generateEstimate)
        self.vSweepCheckBox.toggled.connect(self.generateEstimate)
        self.pwSweepCheckBox.toggled.connect(self.generateEstimate)
        self.pwStartWidget.durationChanged.connect(self.generateEstimate)
        self.pwLimitWidget.durationChanged.connect(self.generateEstimate)
        self.pwSweepComboBox.currentIndexChanged.connect(self.generateEstimate)

        self.pwStartWidget.durationChanged.connect(self.updatePwLimit)
        self.pwLimitWidget.durationChanged.connect(self.updatePwLimit)
        self.readAtSpinBox.setEnabled(False)
        self.readAtComboBox.currentIndexChanged.connect(self.readAtTypeChanged)
        signals.readoutVoltageChanged.connect(self.readoutVoltageChanged)

        self.pwStartWidget.setDuration(10, 'μs')
        self.pwLimitWidget.setDuration(100, 'μs')
        self.targetResistanceWidget.setResistance(100, 'kΩ')

    @property
    def description(self):
        return MOD_DESCRIPTION

    def __populatePolarityComboBox(self):
        box = self.polarityComboBox
        box.addItem('Positive', Polarity.Pos)
        box.addItem('Negative', Polarity.Neg)

    def __populatePulseTypeComboBox(self):
        box = self.pulseTypeComboBox
        box.addItem('Differential', PulseType.Diff)
        box.addItem('Single-ended', PulseType.Single)

    def __populateReadAtComboBox(self):
        box = self.readAtComboBox
        box.addItem('Global (%.2f V)' % self.readoutVoltage, \
            ReadAt.Arb(self.readoutVoltage))
        box.addItem('Override', ReadAt.Bias)

    def __populatepwSweepComboBox(self):
        box = self.pwSweepComboBox
        box.addItem('Geomertic', SweepType.Geo)
        box.addItem('Linear', SweepType.Lin)

    @modaction('selection', desc='Apply to Selection')
    def rampSelected(self):

        if not self.arc2Present(MOD_NAME) or \
            not self.minSelection(MOD_NAME, 1):
            return

        self._thread = AutoFormerOperation(self.__rampParams(), self)
        self._thread.operationFinished.connect(self.__threadFinished)
        self._thread.start()

    def updateVLim(self):
        minimum = self.rampVStartSpinBox.value()
        self.rampVLimSpinBox.setMinimum(minimum)

    def updatePwLimit(self):
        minimum = self.pwStartWidget.getDuration()
        current = self.pwLimitWidget.getDuration()
        minval = self.pwStartWidget.getBaseValue()
        minmult = self.pwStartWidget.getMultiplier()
        currval = self.pwLimitWidget.getBaseValue()
        currmult = self.pwLimitWidget.getMultiplier()
        if currval < minval and currmult == minmult:
            self.pwLimitWidget.setDuration(currval, currmult)
            self.pwLimitWidget.baseValueSpinBox.setMinimum(minval)
        elif current < minimum and currmult != minmult:
            self.pwLimitWidget.setDuration(currval, minmult)
            self.pwLimitWidget.baseValueSpinBox.setMinimum(minval)
        else:
            self.pwLimitWidget.baseValueSpinBox.setMinimum(1)

    def updateResetUI(self):
        reset = self.resetCheckBox.isChecked()
        fullreset = self.fullResetCheckBox.isChecked()
        if reset == True and fullreset != True:
            self.resetStepSpinBox.setEnabled(True)
        else:
            self.resetStepSpinBox.setEnabled(False)

    def generateEstimate(self):
        vstart = self.rampVStartSpinBox.value()
        vstep = self.rampVStepSpinBox.value()
        vlim = self.rampVLimSpinBox.value()
        pulses = self.rampPulsesSpinBox.value()
        pwstart = self.pwStartWidget.getDuration()
        pwlimit = self.pwLimitWidget.getDuration()
        pwstepcount = self.intervalsSpinBox.value()
        pwsweeptype = self.pwSweepComboBox.currentData()
        dopwsweep = self.pwSweepCheckBox.isChecked()
        dovsweep = self.vSweepCheckBox.isChecked()

        if dopwsweep and pwsweeptype == SweepType.Lin:
            pwsweep = np.linspace(pwstart, pwlimit, np.max((pwstepcount, 1)))
        elif dopwsweep and pwsweeptype == SweepType.Geo:
            pwsweep = np.geomspace(pwstart, pwlimit, np.max((pwstepcount, 1)))
        else:
            pwsweep = np.array([pwstart])

        pulsetime = np.sum(pwsweep) + np.size(pwsweep) * 4e-3

        if vstep == 0:
            self.label_estimate.setText("{}".format('NaN'))
        else:
            if dovsweep == False:
                vstepcount = 1
            else:
                vstepcount = np.ceil(((vlim+vstep/2.0) - vstart)/vstep)
            totalsteps = pulses * vstepcount
            esttime = totalsteps * pulsetime
            hours, remainder = divmod(esttime, 3600)
            minutes, seconds = divmod(remainder, 60)
            strhours = str(int(hours)).zfill(2)
            strminutes = str(int(minutes)).zfill(2)
            strseconds = str(int(seconds)).zfill(2)
            self.label_estimate.setText("{}".format(str(strhours + ":" + strminutes + ":" + strseconds)))

    def readoutVoltageChanged(self):
        idx = self.readAtComboBox.currentIndex()
        self.readAtComboBox.clear()
        self.__populateReadAtComboBox()
        self.readAtComboBox.setCurrentIndex(idx)

    def readAtTypeChanged(self, idx):
        readoutType = self.readAtComboBox.itemData(idx)
        self.readAtSpinBox.setEnabled(readoutType == ReadAt.Bias)

    def fromJson(self, frag):
        super().fromJson(frag)

    def __rampParams(self):
        vstart = self.rampVStartSpinBox.value()
        vstep = self.rampVStepSpinBox.value()
        vlim = self.rampVLimSpinBox.value()
        pulses = self.rampPulsesSpinBox.value()
        pwstart = self.pwStartWidget.getDuration()
        pwlimit = self.pwLimitWidget.getDuration()
        pulsetype = self.pulseTypeComboBox.currentData()
        polarity = self.polarityComboBox.currentData()
        if self.readAtComboBox.currentData() == ReadAt.Bias:
            readat = self.readAtSpinBox.value()
        else:
            readat = self.readoutVoltage
        rtarget = self.targetResistanceWidget.getResistance()
        pwsweeptype = self.pwSweepComboBox.currentData()
        pwintervals = self.intervalsSpinBox.value()
        dopwsweep = self.pwSweepCheckBox.isChecked()
        dovsweep = self.vSweepCheckBox.isChecked()
        doreset = self.resetCheckBox.isChecked()
        dofullreset = self.fullResetCheckBox.isChecked()
        resetstep = self.resetStepSpinBox.value()
        deltar = self.rampResetSpinBox.value()
        return (vstart, vstep, vlim, pwstart, pwlimit, pulsetype, polarity, pulses, readat, rtarget, \
            pwsweeptype, pwintervals, dopwsweep, dovsweep, doreset, dofullreset, resetstep, deltar)

    def __threadFinished(self):
        self._thread.wait()
        self._thread.setParent(None)
        data = self._thread.formData()
        (vstart, vstep, vlim, pwstart, pwlimit, pulsetype, polarity, pulses, readat, rtarget, \
            pwsweeptype, pwintervals, dopwsweep, dovsweep, doreset, dofullreset, resetstep, deltar) = \
                self._thread.params
        self._thread = None
        (w, b) = list(self.cells)[0]
        dset = self.datastore.make_wb_table(w, b, MOD_TAG, (len(data[0]), ), _AF_DTYPE)
        vread_array = np.array([readat]).repeat(len(data[0]))
        dset[:, 'voltage'] = data[0]
        dset[:, 'current'] = data[1]
        dset[:, 'read_voltage'] = vread_array
        dset[:, 'pulse_width'] = data[2]

        if dovsweep == True:
            dset.attrs['vstep'] = vstep
        dset.attrs['readat'] = readat
        dset.attrs['pwstart'] = pwstart
        if dopwsweep == True:
            dset.attrs['pwlimit'] = pwlimit
            dset.attrs['pwintervals'] = pwintervals
            dset.attrs['pwsweeptype'] = str(pwsweeptype)
        dset.attrs['pulses'] = pulses
        dset.attrs['polarity'] = str(polarity)
        dset.attrs['pulsetype'] = str(pulsetype)
        if doreset == True:
            dset.attrs['deltar'] = deltar
        if dofullreset == False:
            dset.attrs['resetstep'] = resetstep
        dset.attrs['rtarget'] = rtarget

        optypes = np.array([OpType.PULSEREAD]).repeat(len(data[0]))
        signals.valueBulkUpdate.emit(w, b, data[1], data[0], data[2], vread_array, optypes)
        signals.dataDisplayUpdate.emit(w, b)
        self.experimentFinished.emit(w, b, dset.name)

    @staticmethod
    def display(dataset):
        return AFDataDisplayWidget(dataset)
