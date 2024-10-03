from functools import partial
from PyQt6 import QtCore, QtWidgets
import pyqtgraph as pg
import numpy as np

from arc2control.widgets.datasettable_widget import DatasetTableView

from . import MOD_NAME


_AF_EXPORT_FILE_FILTER = 'Comma separated file (*.csv);;Tab separated file (*.tsv)'


class AFDataDisplayWidget(QtWidgets.QWidget):

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

        #self.stackedWdg.insertWidget(0, self.graphPane)
        #self.stackedWdg.insertWidget(1, self.dataTablePane)
        #self.stackedWdg.insertWidget(2, self.attrsPane)

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

    def __makeGraphPane(self):
        self.graphPane = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        dataset = self.dataset

        current = dataset['current']
        voltage = dataset['voltage']
        pulsewidths = dataset['pulse_width']

        self.gv = pg.GraphicsLayoutWidget()

        self.tracePlot = self.gv.addPlot(name='trace')
        self.tracePlot.showGrid(x=True, y=True)
        self.tracePlot.getAxis('left').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.tracePlot.getAxis('left').setGrid(50)
        self.tracePlot.getAxis('bottom').setGrid(50)
        self.tracePlot.getAxis('left').setLabel('Resistance', units='Ω')
        self.tracePlot.getAxis('left').enableAutoSIPrefix(True)
        self.gv.nextRow()
        self.pulsePlot = self.gv.addPlot(name='pulse')
        self.pulsePlot.showGrid(x=True, y=True)
        self.pulsePlot.getAxis('left').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.pulsePlot.getAxis('left').setGrid(50)
        self.pulsePlot.getAxis('bottom').setGrid(50)
        self.pulsePlot.getAxis('left').setLabel('Pulse voltage', units='V')
        self.pulsePlot.getAxis('left').enableAutoSIPrefix(True)
        self.pulsePlot.setXLink('trace')
        self.gv.nextRow()
        self.widthPlot = self.gv.addPlot(name='width')
        self.widthPlot.showGrid(x=True, y=True)
        self.widthPlot.getAxis('left').setLabel('Pulse width', units='s')
        self.widthPlot.getAxis('left').enableAutoSIPrefix(True)
        self.widthPlot.getAxis('left').setStyle(tickTextWidth=30,\
            autoExpandTextSpace=False)
        self.pulsePlot.getAxis('left').setGrid(50)
        self.pulsePlot.getAxis('bottom').setGrid(50)
        self.widthPlot.setXLink('trace')
        self.widthPlot.getAxis('bottom').setLabel('Pulse')
        self.gv.ci.layout.setRowStretchFactor(0, 3)
        self.gv.ci.layout.setRowStretchFactor(1, 2)
        self.gv.ci.layout.setRowStretchFactor(2, 2)

        self.rangeButtons = QtWidgets.QButtonGroup()
        self.rangeButtonsLabel = QtWidgets.QLabel('X Range:')
        self.fullRangeButton = QtWidgets.QRadioButton('Full')
        self.limRangeButton = QtWidgets.QRadioButton('Limited')
        self.limRangeButton.setChecked(True)
        self.rangeButtons.addButton(self.fullRangeButton)
        self.rangeButtons.addButton(self.limRangeButton)
        self.plotRangeSpinBox = QtWidgets.QSpinBox()
        self.plotRangeSpinBox.setMinimum(1)
        self.plotRangeSpinBox.setMaximum(100000)
        self.plotRangeSpinBox.setValue(200)

        self.limRangeButton.toggled.connect(\
            lambda checked: self.plotRangeSpinBox.setEnabled(checked))
        self.limRangeButton.toggled.connect(self.__replotTraces)
        self.plotRangeSpinBox.valueChanged.connect(self.__replotTraces)

        layout.addWidget(self.gv)
        layout.setContentsMargins(0, 0, 0, 0)

        bottomLayout = QtWidgets.QHBoxLayout()
        bottomLayout.setSpacing(6)

        self.traceLogButton = QtWidgets.QCheckBox('Resistance in log scale')
        self.traceLogButton.toggled.connect(lambda:self.setTraceLog())
        self.traceLogButton.setChecked(True)

        self.widthLogButton = QtWidgets.QCheckBox('Pulse Width in log scale')
        self.widthLogButton.toggled.connect(lambda:self.setWidthLog())
        try:
            pwsweeptype = dataset.attrs['pwsweeptype']
            if pwsweeptype == 'SweepType.Geo':
                self.widthLogButton.setChecked(True)
            else:
                self.widthLogButton.setChecked(False)
        except KeyError:
            self.widthLogButton.setChecked(False)

        bottomLayout.addWidget(self.traceLogButton)
        bottomLayout.addWidget(self.widthLogButton)
        bottomLayout.addStretch()
        bottomLayout.addWidget(self.rangeButtonsLabel)
        bottomLayout.addWidget(self.fullRangeButton)
        bottomLayout.addWidget(self.limRangeButton)
        bottomLayout.addWidget(self.plotRangeSpinBox)
        layout.addItem(bottomLayout)

        self.graphPane.setLayout(layout)
        self.stackedWdg.insertWidget(0, self.graphPane)

        self.__replotTraces()

    def __makePlaceholderWidget(self):
        widget = QtWidgets.QWidget()
        buttonLayout = QtWidgets.QVBoxLayout()
        buttonLayout.setSpacing(6)
        self.forceLoadDatasetButton = QtWidgets.QPushButton("Load anyway")

        buttonLayout.addSpacerItem(\
            QtWidgets.QSpacerItem(20, 20, \
                QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding))
        buttonLayout.addWidget(QtWidgets.QLabel("Dataset has more than 500000 rows"))
        buttonLayout.addWidget(self.forceLoadDatasetButton)
        self.forceLoadDatasetButton.clicked.connect(self.__forceReloadDataTable)
        buttonLayout.addSpacerItem(
            QtWidgets.QSpacerItem(20, 20,
                QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding))

        mainLayout = QtWidgets.QHBoxLayout()
        mainLayout.setSpacing(6)
        mainLayout.addSpacerItem(
            QtWidgets.QSpacerItem(20, 20,
                QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed))
        mainLayout.addLayout(buttonLayout)
        mainLayout.addSpacerItem(
            QtWidgets.QSpacerItem(20, 20,
                QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed))

        widget.setLayout(mainLayout)

        return widget

    def __makeActualDataPane(self):
        self.dataTable = DatasetTableView(self.dataset)
        return self.dataTable

    def __makeDataPane(self, force=False):
        dataset = self.dataset

        self.dataTablePane = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.dataTablePane)
        layout.setContentsMargins(0, 0, 0, 0)

        if dataset.shape[0] < 500000 or force:
            layout.addWidget(self.__makeActualDataPane())
        else:
            layout.addWidget(self.__makePlaceholderWidget())

        buttonLayout = QtWidgets.QHBoxLayout()
        self.exportDataButton = QtWidgets.QPushButton("Export Data")
        self.exportDataButton.clicked.connect(self.exportDataClicked)
        buttonLayout.addSpacerItem(QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))
        buttonLayout.addWidget(self.exportDataButton)
        layout.addLayout(buttonLayout)

        self.dataTablePane.setLayout(layout)
        self.stackedWdg.insertWidget(1, self.dataTablePane)

    def __forceReloadDataTable(self):
        self.dataTablePane.setParent(None)
        del self.dataTablePane
        self.__makeDataPane(True)
        self.stackedWdg.setCurrentIndex(1)

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

        try:
            rtarget = dataset.attrs['rtarget']
            layout.addRow(_makeLabel('Target resistance:'), \
                QtWidgets.QLabel('%s' % pg.siFormat(rtarget, suffix='Ω')))
        except KeyError:
            rtarget = None

        try:
            deltar = dataset.attrs['deltar']
            layout.addRow(_makeLabel('Ramp reset at ΔR of:'), \
                QtWidgets.QLabel(str(deltar) + '%'))
            try:
                resetstep = dataset.attrs['resetstep']
                layout.addRow(_makeLabel('Reset Step:'), \
                    QtWidgets.QLabel('%s' % pg.siFormat(resetstep, suffix='V')))
            except KeyError:
                resetstep = None
        except KeyError:
            deltar = None

        # pulse width
        try:
            readat = dataset.attrs['readat']
            layout.addRow(_makeLabel('Read voltage:'), \
                QtWidgets.QLabel('%s' % pg.siFormat(readat, suffix='V')))
        except KeyError:
            readat = None

        try:
            vstep = dataset.attrs['vstep']
            layout.addRow(_makeLabel('V step:'), \
                QtWidgets.QLabel(pg.siFormat(vstep, suffix='V')))
        except:
            vstep = None

        try:
            pwstart = dataset.attrs['pwstart']
            layout.addRow(_makeLabel('Initial Pulse Width:'), \
                QtWidgets.QLabel(pg.siFormat(pwstart, suffix='s')))
        except:
            pwstart = None

        try:
            pwlimit = dataset.attrs['pwlimit']
            layout.addRow(_makeLabel('Pulse Width Limit:'), \
                QtWidgets.QLabel(pg.siFormat(pwlimit, suffix='s')))
        except:
            pwlimit = None

        try:
            intervals = dataset.attrs['intervals']
            layout.addRow(_makeLabel('# of pulse width steps:'), \
                QtWidgets.QLabel(str(intervals)))
        except KeyError:
            intervals = None

        try:
            pwsweeptype = dataset.attrs['pwsweeptype']
            layout.addRow(_makeLabel('PW sweep type:'), \
                QtWidgets.QLabel(str(pwsweeptype)))
        except KeyError:
            pwsweeptype = None

        try:
            polarity = dataset.attrs['polarity']
            layout.addRow(_makeLabel('Pulses polarity:'), \
                QtWidgets.QLabel(str(polarity)))
        except KeyError:
            polarity = None

        try:
            pulsetype = dataset.attrs['pulsetype']
            layout.addRow(_makeLabel('Pulse type:'), \
                QtWidgets.QLabel(str(pulsetype)))
        except KeyError:
            pulsetype = None

        layout.setItem(layout.rowCount(), \
            QtWidgets.QFormLayout.ItemRole.FieldRole, \
            QtWidgets.QSpacerItem(20, 20, \
            QtWidgets.QSizePolicy.Policy.Expanding, \
            QtWidgets.QSizePolicy.Policy.Expanding))

        attrsWdg.setLayout(layout)
        self.attrsPane.setWidget(attrsWdg)
        self.stackedWdg.insertWidget(2, self.attrsPane)

    def __replotTraces(self):

        self.tracePlot.clear()
        self.pulsePlot.clear()
        self.widthPlot.clear()

        xRange = self.plotRangeSpinBox.value()

        len_timeseries = self.dataset.shape[0]

        if self.fullRangeButton.isChecked() == True:
            timeseries = self.dataset
            offset = 0
        else:
            timeseries = self.dataset[-xRange:]
            offset = max(len_timeseries - xRange, 0)

        idxes = np.arange(offset, len_timeseries)

        self.tracePlot.plot(idxes, np.abs(timeseries['read_voltage']/timeseries['current']),\
            pen={'color': '#F00', 'width': 1}, symbol='+', symbolPen=None, \
            symbolSize=6, symbolBrush='#F00',\
            clear=True)

        # plot the pulse points
        self.pulsePlot.plot(idxes, timeseries['voltage'], pen=None,\
            symbolPen=None, symbolBrush=(0, 150, 150),  symbol='s',\
            symbolSize=6, clear=True)

        # plot the impulse lines
        self.pulsePlot.plot(np.repeat(idxes, 2), \
            np.dstack((\
                np.zeros(len(timeseries['voltage'])), timeseries['voltage'])
            ).flatten(), \
            pen=(0, 150, 150),\
            connect='pairs')

        # plot the read points
        self.pulsePlot.plot(idxes, timeseries['read_voltage'], pen=None,\
            symbolPen=None, symbolBrush=(0, 0, 255),  symbol='+',\
            symbolSize=6)

        # plot the pulse widths
        self.widthPlot.plot(idxes, timeseries['pulse_width'], pen=None,\
            symbolPen=None, symbolBrush=(0, 170, 0),  symbol='+',\
            symbolSize=6)

        self.setTraceLog()
        self.setWidthLog()

    def setTraceLog(self):
        if self.traceLogButton.isChecked() == True:
            self.tracePlot.setLogMode(False, True)
        else:
            self.tracePlot.setLogMode(False, False)

    def setWidthLog(self):
        if self.widthLogButton.isChecked() == True:
            self.widthPlot.setLogMode(False, True)
        else:
            self.widthPlot.setLogMode(False, False)


    def exportDataClicked(self):
        (fname, fltr) = QtWidgets.QFileDialog.getSaveFileName(self, \
            "Export data from %s" % MOD_NAME, '', _AF_EXPORT_FILE_FILTER)

        dataset = self.dataset

        # save dataset attributes in the header
        header = []
        header.append(' ATTRS_START')
        header.append(' crosspoints: %s' % dataset.attrs['crosspoints'][0])

        for key in ['vstep', 'readat', 'pwstart', 'pwlimit', 'pulses', 'rtarget']:
            try:
                header.append(' %s: %g' % (key, dataset.attrs[key]))
            except KeyError:
                continue

        for key in ['pwsweeptype', 'polarity', 'pulsetype']:
            try:
                header.append(' %s: %s' % (key, dataset.attrs[key]))
            except KeyError:
                continue

        header.append(' ATTRS_END')
        header.append('')
        header.append(' voltage,resistance,read_voltage,pulse_width')

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


