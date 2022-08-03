import os.path
from PyQt6 import QtCore, QtWidgets
from functools import partial
from .generated.crossbarconf import Ui_CrossbarConfigDialog
from ..graphics import getPixmap, getIcon
from ..h5utils import H5DataStore, H5Mode

from .. import ArC2ControlSettings
from .. import constants


class CrossbarConfigDialog(Ui_CrossbarConfigDialog, QtWidgets.QDialog):

    def __init__(self, mappers, parent=None):
        Ui_CrossbarConfigDialog.__init__(self)
        QtWidgets.QDialog.__init__(self, parent=parent)
        self.mappers = mappers

        self.setupUi(self)
        self.setWindowIcon(getIcon('arc2-logo'))
        self.logoLabel.setPixmap(getPixmap('splash'))
        self.__populateMappers()
        self.__populateDatasets()
        self.nwords = 32
        self.nbits = 32

        self.wdgGroup = {}
        self.wdgGroup[self.sizeRadioButton] = \
            [self.wordsSpinBox, self.bitsSpinBox, \
             self.wordsLabel, self.bitsLabel]
        self.wdgGroup[self.mapperRadioButton] = \
            [self.mapperSelectionComboBox]
        self.wdgGroup[self.datasetRadioButton] = \
            [self.datasetSelectionComboBox, self.selectDatasetButton,\
             self.loadDatasetCheckBox]

        for wdg in self.wdgGroup.keys():
            wdg.toggled.connect(partial(self.__sizeSpecificationChanged, wdg))

        self.selectDatasetButton.clicked.connect(self.__selectDatasetClicked)
        self.datasetSelectionComboBox.currentIndexChanged.connect(self.__datasetSelectionChanged)
        self.mapperSelectionComboBox.currentIndexChanged.connect(self.__mapperSelectionChanged)
        self.wordsSpinBox.valueChanged.connect(self.__manualSizeChanged)
        self.bitsSpinBox.valueChanged.connect(self.__manualSizeChanged)

    def result(self):

        result = {}

        if self.datasetRadioButton.isChecked() and self.datasetSelectionComboBox.count() > 0 and \
            self.loadDatasetCheckBox.isChecked():
            result['dataset'] = self.datasetSelectionComboBox.currentData()[0]
        else:
            result['dataset'] = None

        if self.mapperRadioButton.isChecked():
            result['mapper'] = self.mapperSelectionComboBox.currentData()[0]
        else:
            result['mapper'] = None

        result['nwords'] = self.nwords
        result['nbits'] = self.nbits

        return result

    def accept(self, *args):

        # if user selected a dataset bring the last selection forward
        if self.datasetRadioButton.isChecked():

            currentIdx = self.datasetSelectionComboBox.currentIndex()

            if currentIdx == 0:
                # selected dataset is indeed the latest; nothing to do
                return QtWidgets.QDialog.accept(self, *args)

            settings = ArC2ControlSettings

            dsets = []
            # add the latest selected dataset first
            dsets.append(self.datasetSelectionComboBox.currentData())

            # and all the others afterwards
            for i in range(self.datasetSelectionComboBox.count()):
                if currentIdx != i:
                    dsets.append(self.datasetSelectionComboBox.itemData(i))

            # updated the recent dataset config on disk
            settings.setValue('crossbarconfig/datasets', dsets[:10])

        QtWidgets.QDialog.accept(self, *args)

    def __updateSelectedSize(self, wdg):
        if wdg is self.sizeRadioButton:
            nwords = self.wordsSpinBox.value()
            nbits = self.bitsSpinBox.value()
        elif wdg is self.mapperRadioButton:
            mapper = self.mapperSelectionComboBox.currentData()[1]
            nwords = mapper.nwords
            nbits = mapper.nbits
        elif wdg is self.datasetRadioButton:
            if self.datasetSelectionComboBox.count() == 0:
                self.__selectDatasetClicked()
            try:
                (_, nwords, nbits) = self.datasetSelectionComboBox.currentData()
            except TypeError: # nothing selected
                return

        self.nwords = nwords
        self.nbits = nbits

    def __populateMappers(self):

        lbl = "%s (%d×%d)"

        for (key, mapper) in self.mappers.items():
            label = lbl % (mapper.name, mapper.nwords, mapper.nbits)
            self.mapperSelectionComboBox.addItem(label, (key, mapper))

        self.mapperSelectionComboBox.setCurrentIndex(0)

    def __populateDatasets(self):

        settings = ArC2ControlSettings

        dsets = settings.value('crossbarconfig/datasets')

        if dsets is None:
            return

        removedIdxs = []

        for (idx, (dset, nwords, nbits)) in enumerate(dsets):
            lbl = "%s (%d×%d)" % (os.path.basename(dset), nwords, nbits)
            if os.path.exists(dset):
                self.datasetSelectionComboBox.addItem(lbl, (dset, nwords, nbits))
                # add the full name to the tooltip
                self.datasetSelectionComboBox.setItemData(idx, dset, \
                    QtCore.Qt.ItemDataRole.ToolTipRole)
            else:
                removedIdxs.append(idx)

        # remove any datasets that don't exist and update local config file
        if len(removedIdxs) > 0:
            for idx in removedIdxs:
                dsets.pop(idx)
            settings.setValue('crossbarconfig/datasets', dsets[:10])

    def __sizeSpecificationChanged(self, wdg, status):
        for (k, v) in self.wdgGroup.items():
            if k is wdg:
                enable = True
            else:
                enable = False

            for w in v:
                w.setEnabled(enable)

        self.__updateSelectedSize(wdg)

    def __selectDatasetClicked(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, "Open dataset",\
            '', constants.H5_FILE_FILTER)

        if fname is None or len(fname[0]) == 0:
            return

        fname = fname[0]

        with H5DataStore(fname, mode=H5Mode.READ) as dset:
            nwords = dset['crossbar'].attrs['words']
            nbits = dset['crossbar'].attrs['bits']
            self.datasetSelectionComboBox.insertItem(0, \
                "%s (%d×%d)" % (os.path.basename(fname), nwords, nbits), \
                    (fname, nwords, nbits))
            self.datasetSelectionComboBox.setCurrentIndex(0)

            self.nwords = nwords
            self.nbits = nbits

        dsetList = ArC2ControlSettings.value('crossbarconfig/datasets')
        if dsetList is None:
            dsetList = [(fname, int(self.nwords), int(self.nbits))]
        else:
            dsetList.insert(0, (fname, int(self.nwords), int(self.nbits)))

        ArC2ControlSettings.setValue('crossbarconfig/datasets', dsetList[:10])

    def __mapperSelectionChanged(self, _):
        mapper = self.mapperSelectionComboBox.currentData()[1]
        self.nwords = mapper.nwords
        self.nbits = mapper.nbits

    def __datasetSelectionChanged(self, _):
        (_, nwords, nbits) = self.datasetSelectionComboBox.currentData()
        self.nwords = nwords
        self.nbits = nbits

    def __manualSizeChanged(self, _):
        self.nwords = self.wordsSpinBox.value()
        self.nbits = self.bitsSpinBox.value()

