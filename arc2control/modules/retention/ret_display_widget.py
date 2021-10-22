from functools import partial
from PyQt6 import QtWidgets
import pyqtgraph as pg
import numpy as np

from . import MOD_TAG, MOD_NAME


_RET_EXPORT_FILE_FILTER = 'Comma separated file (*.csv);;Tab separated file (*.tsv)'


class RETDataDisplayWidget(QtWidgets.QWidget):

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
            self.__displaySelectionChanged, btn=self.dataButton))
        self.graphButton = QtWidgets.QPushButton("Graph")
        self.graphButton.setCheckable(True)
        self.graphButton.toggled.connect(partial(\
            self.__displaySelectionChanged, btn=self.graphButton))

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

        self.__makeGraphPane()
        self.__makeDataPane()

        try:
            crosspoint = self.dataset.attrs['crosspoints'][0]
            self.setProperty('title', '%s | W = %02d B = %02d' % \
                (MOD_NAME, crosspoint[0]+1, crosspoint[1]+1))
        except KeyError:
            self.setProperty('title', '%s' % (MOD_NAME))

        self.setProperty('recsize', (800, 500))

        self.stackedWdg.addWidget(self.gv)
        self.stackedWdg.addWidget(self.dataTablePane)

        layout.addWidget(self.stackedWdg)
        self.setLayout(layout)

    def __displaySelectionChanged(self, checked, btn):
        if not checked:
            return
        if checked == self.graphButton.isChecked():
            self.stackedWdg.setCurrentIndex(0)
        elif checked == self.dataButton.isChecked():
            self.stackedWdg.setCurrentIndex(1)

    def __makeGraphPane(self):

        dataset = self.dataset

        resistance = np.abs(dataset['read_voltage']/dataset['current'])

        t0 = dataset['tstamp_s'][0]*1.0 + dataset['tstamp_us'][0]/1.0e6
        timestamps = (dataset['tstamp_s']*1.0 + dataset['tstamp_us']/1.0e6) - t0

        self.gv = pg.GraphicsLayoutWidget()
        self.plot = self.gv.addPlot()
        self.plot.getAxis('left').setLabel('Resistance', units='Ω')
        self.plot.getAxis('bottom').setLabel('Time', units='s')
        self.plot.showGrid(x=True, y=True)
        self.plot.getAxis('left').setGrid(50)
        self.plot.getAxis('bottom').setGrid(50)

        self.plot.plot(timestamps, resistance, pen='r', symbolBrush='r', \
            symbolPen=None, symbol='+', symbolSize=6)

    def __makeDataPane(self):

        dataset = self.dataset

        dataDisplayDType = [('time', '<f8'), \
            ('voltage', '<f4'), ('current', '<f4'), ('resistance', '<f4')]

        self.dataTable = pg.TableWidget(sortable=False, editable=False)
        self.dataTable.setFormat('%.3f', 0)
        self.dataTable.setFormat('%f', 1)
        self.dataTable.setFormat('%e', 2)
        self.dataTable.setFormat('%g', 3)
        self.dataTable.verticalHeader().setVisible(False)
        resistance = np.abs(dataset['read_voltage']/dataset['current'])
        t0 = dataset['tstamp_s'][0]*1.0 + dataset['tstamp_us'][0]/1.0e6
        timestamps = (dataset['tstamp_s']*1.0 + dataset['tstamp_us']/1.0e6) - t0

        actual_data = np.empty(shape=(dataset.shape[0],), dtype=dataDisplayDType)

        actual_data['time'][:] = timestamps[:]
        actual_data['voltage'][:] = dataset['read_voltage'][:]
        actual_data['current'][:] = dataset['current'][:]
        actual_data['resistance'][:] = resistance[:]

        self.dataTable.setData(actual_data)
        self.data = actual_data

        self.dataTablePane = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.dataTablePane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.dataTable)

        buttonLayout = QtWidgets.QHBoxLayout()
        self.exportDataButton = QtWidgets.QPushButton("Export Data")
        self.exportDataButton.clicked.connect(self.exportDataClicked)
        buttonLayout.addSpacerItem(QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, \
            QtWidgets.QSizePolicy.Policy.Minimum))
        buttonLayout.addWidget(self.exportDataButton)
        layout.addLayout(buttonLayout)

        self.dataTablePane.setLayout(layout)

    def exportDataClicked(self):
        (fname, fltr) = QtWidgets.QFileDialog.getSaveFileName(self, \
            "Export data from %s" % MOD_NAME, '', _RET_EXPORT_FILE_FILTER)

        if fname is None or len(fname) == 0:
            return

        if fltr.endswith('csv)'):
            delimiter = ','
        elif fltr.endswith('tsv)'):
            delimiter = '\t'
        else:
            delimiter = ','

        np.savetxt(fname, self.data, delimiter=delimiter)
