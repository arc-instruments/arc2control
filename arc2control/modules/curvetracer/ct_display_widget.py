from functools import partial
from PyQt6 import QtWidgets
import pyqtgraph as pg
import numpy as np

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
            self._displaySelectionChanged, btn=self.dataButton))
        self.graphButton = QtWidgets.QPushButton("Graph")
        self.graphButton.setCheckable(True)
        self.graphButton.toggled.connect(partial(\
            self._displaySelectionChanged, btn=self.graphButton))

        buttonGroup.addButton(self.graphButton)
        buttonGroup.addButton(self.dataButton)

        buttonLayout.addItem(QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))
        buttonLayout.addWidget(self.graphButton)
        buttonLayout.addWidget(self.dataButton)
        buttonLayout.addItem(QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        self.graphButton.setChecked(True)

        layout.addLayout(buttonLayout)

        self._makeGraphPane()
        self._makeDataPane()

        try:
            crosspoint = self.dataset.attrs['crosspoints'][0]
            self.setProperty('title', '%s | W=%02d B = %02d' % \
                (MOD_NAME, crosspoint[0], crosspoint[1]))
        except KeyError:
            self.setProperty('title', '%s' % (MOD_NAME))

        self.setProperty('recsize', (800, 500))

        self.stackedWdg.addWidget(self.gv)

        self.stackedWdg.addWidget(self.dataTablePane)

        layout.addWidget(self.stackedWdg)
        self.setLayout(layout)

    def _displaySelectionChanged(self, checked, btn):
        if not checked:
            return
        if checked == self.graphButton.isChecked():
            self.stackedWdg.setCurrentIndex(0)
        elif checked == self.dataButton.isChecked():
            self.stackedWdg.setCurrentIndex(1)

    def _makeGraphPane(self):
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

        for (idx, chunk) in enumerate(np.array_split(dataset, cycles)):
            self.plotI.plot(chunk['voltage'], chunk['current'], pen=(idx, cycles), \
                symbolBrush=(idx, cycles), symbolPen=None, symbol='s', symbolSize=6)
            self.plotAbsI.plot(chunk['voltage'], np.abs(chunk['current']), \
                pen=(idx, cycles), symbolBrush=(idx, cycles), symbolPen=None, \
                symbol='s', symbolSize=6)
            self.plotR.plot(chunk['voltage'], \
                np.abs(chunk['voltage'])/np.abs(chunk['current']), \
                pen=(idx, cycles), symbolBrush=(idx, cycles), symbolPen=None, \
                symbol='s', symbolSize=6)

    def _makeDataPane(self):
        dataset = self.dataset

        cycles = dataset.attrs.get('cycles', 1)

        if dataset.shape[0] % cycles > 0:
            len_per_cycle = (dataset.shape[0]+1) // cycles
            # we will need to duplicate a point in order to
            # have equally sized arrays PER CYCLE
            needs_adjustment = True
        else:
            len_per_cycle = dataset.shape[0] // cycles
            needs_adjustment = False

        self.dataTable = pg.TableWidget(sortable=False, editable=False)
        self.dataTable.setFormat('%e')
        self.dataTable.verticalHeader().setVisible(False)

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
                from_idx = i*len_per_cycle
                to_idx = from_idx + len_per_cycle

                for f in ['current', 'voltage', 'read_voltage']:
                    actual_data[f+str(i+1)][from_idx:to_idx] = dataset[from_idx:to_idx, f]

            # special handling for the last cycle that's one point shorter than the rest
            if needs_adjustment:
                # copy the last point from the last cycle as the first point of the last
                # cycle to account for that missing last point
                for f in ['current', 'voltage', 'read_voltage']:
                    actual_data[f+str(cycles)][0] = dataset[to_idx-1, f]

                    actual_data[f+str(cycles)][1:] = \
                        dataset[to_idx:, f]

            self.data = actual_data
        else:
            self.data = dataset[:]

        self.dataTable.setData(self.data)

        self.dataTablePane = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.dataTablePane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.dataTable)

        buttonLayout = QtWidgets.QHBoxLayout()
        self.exportDataButton = QtWidgets.QPushButton("Export Data")
        self.exportDataButton.clicked.connect(self._exportDataClicked)
        buttonLayout.addSpacerItem(QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))
        buttonLayout.addWidget(self.exportDataButton)
        layout.addLayout(buttonLayout)

        self.dataTablePane.setLayout(layout)

    def _exportDataClicked(self):
        (fname, fltr) = QtWidgets.QFileDialog.getSaveFileName(self, \
            "Export data from %s" % MOD_NAME, '', _CT_EXPORT_FILE_FILTER)

        if fname is None or len(fname) == 0:
            return

        if fltr.endswith('csv)'):
            delimiter = ','
        elif fltr.endswith('tsv)'):
            delimiter = '\t'
        else:
            delimiter = ','

        np.savetxt(fname, self.data, delimiter=delimiter)


