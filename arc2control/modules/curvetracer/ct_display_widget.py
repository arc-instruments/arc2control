from itertools import groupby
from functools import partial
from PyQt6 import QtCore, QtWidgets
from pyarc2 import ReadAfter
import pyqtgraph as pg
import numpy as np

from arc2control.widgets.datasettable_widget import DatasetTableView

from . import MOD_TAG, MOD_NAME


_CT_EXPORT_FILE_FILTER = 'Comma separated file (*.csv);;Tab separated file (*.tsv)'


class CTDataDisplayWidget(QtWidgets.QWidget):

    def __init__(self, dataset, parent=None):
        super().__init__(parent=parent)
        self.dataset = dataset
        self.setupUi()

    def setupUi(self):
        self.stackedWdg = QtWidgets.QStackedWidget()

        layout = QtWidgets.QVBoxLayout()

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonGroup = QtWidgets.QButtonGroup(self)
        self.dataButton = QtWidgets.QPushButton("Data")
        self.dataButton.setCheckable(True)
        self.dataButton.toggled.connect(partial(\
            self.displaySelectionChanged, btn=self.dataButton))
        self.graphButton = QtWidgets.QPushButton("Graph")
        self.graphButton.setCheckable(True)
        self.graphButton.toggled.connect(partial(\
            self.displaySelectionChanged, btn=self.graphButton))
        self.attrsButton = QtWidgets.QPushButton("Attributes")
        self.attrsButton.setCheckable(True)
        self.attrsButton.toggled.connect(partial(\
            self.displaySelectionChanged, btn=self.attrsButton))

        buttonGroup.addButton(self.graphButton)
        buttonGroup.addButton(self.dataButton)
        buttonGroup.addButton(self.attrsButton)

        buttonLayout.addItem(QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))
        buttonLayout.addWidget(self.graphButton)
        buttonLayout.addWidget(self.dataButton)
        buttonLayout.addWidget(self.attrsButton)
        buttonLayout.addItem(QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        self.graphButton.setChecked(True)

        layout.addLayout(buttonLayout)

        self.data = self.__reformatData()
        self.__makeGraphPane()
        self.__makeDataPane()
        self.__makeAttrsPane()

        try:
            crosspoint = self.dataset.attrs['crosspoints'][0]
            self.setProperty('title', '%s | W = %02d B = %02d' % \
                (MOD_NAME, crosspoint[0]+1, crosspoint[1]+1))
        except KeyError:
            self.setProperty('title', '%s' % (MOD_NAME))

        self.setProperty('recsize', (800, 500))

        self.stackedWdg.addWidget(self.graphPane)
        self.stackedWdg.addWidget(self.dataTablePane)
        self.stackedWdg.addWidget(self.attrsPane)

        layout.addWidget(self.stackedWdg)
        self.setLayout(layout)

    def displaySelectionChanged(self, checked, btn):
        if not checked:
            return
        if checked == self.graphButton.isChecked():
            self.stackedWdg.setCurrentIndex(0)
        elif checked == self.dataButton.isChecked():
            self.stackedWdg.setCurrentIndex(1)
        elif checked == self.attrsButton.isChecked():
            self.stackedWdg.setCurrentIndex(2)

    def __reformatData(self):
        dataset = self.dataset
        cycles = dataset.attrs.get('cycles', 1)

        if dataset.shape[0] % cycles > 0:
            len_per_cycle = (dataset.shape[0] // cycles) + 1
            # we will need to duplicate a point per cycle in order to
            # have equally sized arrays PER CYCLE
            needs_adjustment = True
        else:
            len_per_cycle = dataset.shape[0] // cycles
            needs_adjustment = False

        # if a test has more than one cycles the dataset it must be split
        # into multiple columns (3 per cycle) because at rest is a
        # long contiguous array.
        if cycles > 1:
            dtype = dataset.dtype.descr
            dtype_len = len(dataset.dtype.descr)

            dtype = []
            for i in range(cycles):
                for (title, dt) in dataset.dtype.descr:
                    dtype.append(('%s%d' % (title, i+1), dt))

            actual_data = np.empty(shape=(len_per_cycle,), dtype=dtype)

            if needs_adjustment:
                cycles_to_process = cycles - 1
            else:
                cycles_to_process = cycles

            # if the dataset needs adjustment process all the cycles but the
            # last one, otherwise just process all of them
            for i in range(cycles_to_process):
                from_idx = i*(len_per_cycle-1)
                to_idx = from_idx + (len_per_cycle-1)

                for f in ['current', 'voltage', 'read_voltage']:
                    if needs_adjustment:
                        # copy the data into the first len_per_cycle-1 points
                        actual_data[f+str(i+1)][0:len_per_cycle-1] = dataset[from_idx:to_idx, f]
                        # and copy the first point of the next cycle as the last point of this
                        # cycle to make all columns equal length
                        actual_data[f+str(i+1)][len_per_cycle-1] = dataset[to_idx, f]

                    else:
                        actual_data[f+str(i+1)][:] = dataset[i*len_per_cycle:(i+1)*len_per_cycle, f]

            # special handling for the last cycle that's one point longer than the rest
            if needs_adjustment:
                for f in ['current', 'voltage', 'read_voltage']:
                    actual_data[f+str(cycles)][:] = dataset[to_idx:, f]

            return actual_data
        else:
            return dataset[:]

    def __cycleData(self, idx=0):
        cycles = self.dataset.attrs.get('cycles', 1)

        if idx > cycles - 1:
            raise IndexError('No such cycle: %d' % idx)

        if idx == 0 and cycles == 1:
            suffix = ''
        else:
            suffix = str(idx+1)

        return { 'voltage': self.data['voltage'+suffix],
            'current': self.data['current'+suffix],
            'read_voltage': self.data['read_voltage'+suffix] }


    def __makeGraphPane(self):
        self.graphPane = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        dataset = self.dataset

        cycles = dataset.attrs.get('cycles', 1)
        current = dataset['current']
        voltage = dataset['voltage']

        self.gv = pg.GraphicsLayoutWidget()
        self.plotI = self.gv.addPlot()
        self.plotAbsI = self.gv.addPlot()
        self.plotR = self.gv.addPlot()
        self.plotI.getAxis('bottom').setLabel('Voltage', units='V')
        self.plotI.getAxis('left').setLabel('Current', units='A')
        self.plotI.showGrid(x=True, y=True)
        self.plotI.getAxis('left').setGrid(50)
        self.plotI.getAxis('bottom').setGrid(50)
        self.plotAbsI.getAxis('bottom').setLabel('Voltage', units='V')
        self.plotAbsI.getAxis('left').setLabel('Current', units='A')
        self.plotAbsI.getAxis('left').enableAutoSIPrefix(False)
        self.plotAbsI.setLogMode(False, True)
        self.plotAbsI.showGrid(x=True, y=True)
        self.plotAbsI.getAxis('left').setGrid(50)
        self.plotAbsI.getAxis('bottom').setGrid(50)
        self.plotR.getAxis('bottom').setLabel('Voltage', units='V')
        self.plotR.getAxis('left').setLabel('Resistance', units='Ω')
        self.plotR.showGrid(x=True, y=True)
        self.plotR.getAxis('left').setGrid(50)
        self.plotR.getAxis('bottom').setGrid(50)

        self.__replotTraces()

        layout.addWidget(self.gv)
        layout.setContentsMargins(0, 0, 0, 0)

        bottomLayout = QtWidgets.QHBoxLayout()
        self.averagingCheckBox = QtWidgets.QCheckBox('Average traces')
        self.averagingCheckBox.stateChanged.connect(self.__replotTraces)
        bottomLayout.addWidget(self.averagingCheckBox)

        layout.addItem(bottomLayout)

        self.graphPane.setLayout(layout)

    def __makeDataPane(self):
        dataset = self.dataset

        cycles = dataset.attrs.get('cycles', 1)

        self.dataTable = DatasetTableView(self.data)

        self.dataTablePane = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.dataTablePane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.dataTable)

        buttonLayout = QtWidgets.QHBoxLayout()
        self.exportDataButton = QtWidgets.QPushButton("Export Data")
        self.exportDataButton.clicked.connect(self.exportDataClicked)
        buttonLayout.addSpacerItem(QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))
        buttonLayout.addWidget(self.exportDataButton)
        layout.addLayout(buttonLayout)

        self.dataTablePane.setLayout(layout)

    def __makeAttrsPane(self):

        def _makeLabel(text):
            lbl = QtWidgets.QLabel(text)
            lbl.setStyleSheet('QLabel { font-weight: bold; }')

            return lbl

        dataset = self.dataset
        (word, bit) = (dataset.attrs['crosspoints'][0])

        self.attrsPane = QtWidgets.QScrollArea(self)
        attrsWdg = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout()
        layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.setVerticalSpacing(12)

        layout.addRow(_makeLabel('Crosspoint:'), \
            QtWidgets.QLabel('W: %02d B: %02d' % (word+1, bit+1)))
        layout.addRow(_makeLabel('Cycles:'), \
            QtWidgets.QLabel(str(dataset.attrs['cycles'])))

        # interpulse
        try:
            interpulse = dataset.attrs['inter']
            if interpulse == 0:
                layout.addRow(_makeLabel('Type:'), QtWidgets.QLabel('Staircase'))
            else:
                layout.addRow(_makeLabel('Type:'), \
                    QtWidgets.QLabel('Pulsed (interpulse: %s)' \
                        % pg.siFormat(interpulse, suffix='s')))
        except KeyError:
            interpulse = None

        # pulse width
        try:
            pw = dataset.attrs['pw']
            if interpulse is not None and interpulse == 0:
                pwlabel = _makeLabel('Step width:')
            elif interpulse is not None and interpulse > 0:
                pwlabel = _makeLabel('Pulse width:')
            else:
                pwlabel = _makeLabel('Step width:')
            layout.addRow(pwlabel, \
                QtWidgets.QLabel('%s' % pg.siFormat(pw, suffix='s')))
        except KeyError:
            pw = None

        try:
            vstep = dataset.attrs['vstep']
            layout.addRow(_makeLabel('V step:'), \
                QtWidgets.QLabel(pg.siFormat(vstep, suffix='V')))
        except:
            vstep = None

        try:
            pulses = dataset.attrs['pulses']
            layout.addRow(_makeLabel('Pulses per step:'), \
                QtWidgets.QLabel(str(pulses)))
        except KeyError:
            pulses = None

        try:
            readafter = dataset.attrs['read_after']
            ralabel = _makeLabel('Read after:')
            if readafter == str(ReadAfter.Pulse):
                layout.addRow(ralabel, QtWidgets.QLabel('Pulse'))
            elif readafter == str(ReadAfter.Block):
                layout.addRow(ralabel, QtWidgets.QLabel('Block'))
            else:
                layout.addRow(ralabel, QtWidgets.QLabel('Unknown'))
        except Exception as exc:
            readafter = None

        try:
            ramp = dataset.attrs['ramp']
            plotWdg = pg.PlotWidget()
            plotWdg.setMouseEnabled(False, False)
            plotWdg.setMenuEnabled(False)
            plotWdg.setMinimumSize(200, 120)
            plotWdg.setMaximumSize(500, 120)
            plotWdg.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed)
            plotWdg.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            minV = np.min(ramp.flatten())
            maxV = np.max(ramp.flatten())

            maxLine = pg.InfiniteLine(maxV, angle=0.0, label="max = %s" % \
                pg.siFormat(maxV, suffix='V'), labelOpts={'color': '#000'})
            minLine = pg.InfiniteLine(minV, angle=0.0, label="min = %s"% \
                pg.siFormat(minV, suffix='V'), labelOpts={'color': '#000'})

            plot = plotWdg.plot([a for a,b in groupby(ramp.flatten())], pen={'color': '#00F', 'width': 2})
            plotWdg.getPlotItem().hideAxis('bottom')
            plotWdg.getPlotItem().getAxis('left').setLabel('Voltage', units='V')
            plotWdg.addItem(maxLine)
            plotWdg.addItem(minLine)
            layout.addRow(_makeLabel('Ramp:'), plotWdg)
        except KeyError:
            ramp = None

        layout.setItem(layout.rowCount(), \
            QtWidgets.QFormLayout.ItemRole.FieldRole, \
            QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, \
            QtWidgets.QSizePolicy.Policy.Expanding))

        attrsWdg.setLayout(layout)
        self.attrsPane.setWidget(attrsWdg)

    def __replotTraces(self, showAverage=False):

        self.plotI.clear()
        self.plotAbsI.clear()
        self.plotR.clear()

        data = self.data
        cycles = self.dataset.attrs.get('cycles', 1)

        average = np.ndarray(shape=(data.shape[0], ), \
            dtype=[('voltage', '<f4'), ('current', '<f4')])
        average['voltage'][:] = self.__cycleData(0)['voltage']
        average['current'][:] = 0.0

        for idx in range(0, cycles):

            if showAverage:
                pen = 'grey'
                symbolBrush = None
                symbol = None
                symbolSize = 0
            else:
                pen = (idx, cycles)
                symbolBrush = (idx, cycles)
                symbol = 's'
                symbolSize = 6

            suffix = str(idx+1) if cycles > 1 else ''
            cycleData = self.__cycleData(idx)

            voltage = cycleData['voltage']
            current = cycleData['current']

            self.plotI.plot(voltage, current, \
                pen=pen, symbolBrush=symbolBrush, symbolPen=None,
                symbol=symbol, symbolSize=symbolSize)
            self.plotAbsI.plot(voltage, np.abs(current), \
                pen=pen, symbolBrush=symbolBrush, symbolPen=None,
                symbol=symbol, symbolSize=symbolSize)
            self.plotR.plot(voltage, \
                np.abs(voltage/current), \
                pen=pen, symbolBrush=symbolBrush, symbolPen=None,
                symbol=symbol, symbolSize=symbolSize)

            average['current'][:] += data['current'+suffix]

        average['current'][:] = average['current']/cycles
        if showAverage:
            pen = pg.mkPen(color='red', width=2.0)
            self.plotI.plot(average['voltage'], average['current'], \
                pen=pen, symbolBrush=None, symbol=None, clear=False)
            self.plotAbsI.plot(average['voltage'], np.abs(average['current']), \
                pen=pen, symbolBrush=None, symbol=None, clear=False)
            self.plotR.plot(average['voltage'], \
                np.abs(average['voltage']/average['current']), \
                pen=pen, symbolBrush=None, symbol=None, clear=False)

    def exportDataClicked(self):
        (fname, fltr) = QtWidgets.QFileDialog.getSaveFileName(self, \
            "Export data from %s" % MOD_NAME, '', _CT_EXPORT_FILE_FILTER)

        dataset = self.dataset

        # save dataset attributes in the header
        header = []
        header.append(' ATTRS_START')
        header.append(' crosspoints: %s' % dataset.attrs['crosspoints'][0])
        header.append(' cycles: %d' % dataset.attrs['cycles'])

        try:
            ramp = dataset.attrs['ramp'].flatten()
            header.append(' ramp: %s' % str(ramp))
            header.append(' minV: %d' % np.min(ramp))
            header.append(' maxV: %s' % np.max(ramp))
        except KeyError:
            pass

        try:
            readafter = dataset.attrs['read_after']
            header.append(' read after: %s' % str(readafter))
        except KeyError:
            pass

        for key in ['vstep', 'pw', 'pulses', 'inter']:
            try:
                header.append(' %s: %g' % (key, dataset.attrs[key]))
            except KeyError:
                continue

        header.append(' ATTRS_END')
        header.append('')
        header.append(' voltage,current,read_voltage')

        if fname is None or len(fname) == 0:
            return

        if fltr.endswith('csv)'):
            delimiter = ','
        elif fltr.endswith('tsv)'):
            delimiter = '\t'
        else:
            delimiter = ','

        np.savetxt(fname, self.data, comments='#', header='\n'.join(header), \
            delimiter=delimiter)


