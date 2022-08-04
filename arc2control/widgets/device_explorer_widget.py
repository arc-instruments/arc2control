from PyQt6 import QtCore, QtWidgets
from pathlib import PurePosixPath
from functools import partial
import re


_keyMatcher = re.compile('W(\d+)B(\d+)')


def _experimentSorter(item):
    (tag, tstamp) = item.split('_')
    return int(tstamp)


def _wbFromKey(key):

    match = _keyMatcher.match(key)

    if not match:
        return (None, None)

    return (int(match.group(1)), int(match.group(2)))

class DeviceExplorerWidget(QtWidgets.QWidget):

    #                                      tag, path
    experimentSelected = QtCore.pyqtSignal(str, str)
    #                                                w,   b,   complete
    exportDeviceHistoryRequested = QtCore.pyqtSignal(int, int, bool)
    #                                      w,   b
    crosspointSelected = QtCore.pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.__itemRightClicked)

        self._root = QtWidgets.QTreeWidgetItem(self.tree, ['Root'])
        self._deviceNodes = {}
        self._tagMapper = None
        self.tree.setRootIndex(self.tree.indexFromItem(self._root))
        self.tree.itemSelectionChanged.connect(self.__itemSelected)
        self.tree.itemDoubleClicked.connect(self.__itemDoubleClicked)

        self.layout.addWidget(self.tree)

    def __itemSelected(self):
        try:
            item = self.tree.selectedItems()[0]
        except IndexError:
            self.crosspointSelected.emit(-1, -1)
            return

        toplevel = item

        while toplevel.parent() != self._root:
            toplevel = toplevel.parent()

        if toplevel != self._root:
            self.crosspointSelected.emit(toplevel.word, toplevel.bit)

    def __itemDoubleClicked(self, item, _):
        if item.parent() == self._root:
            return

        self.experimentSelected.emit(item.modtag, item.path)

    def __itemRightClicked(self, point):
        item = self.tree.itemAt(point)
        try:
            key = item.key
            menu = QtWidgets.QMenu("Context Menu", self)
            exportAllAction = menu.addAction('Export complete history')
            exportAllAction.triggered.connect(\
                partial(self.__exportTriggered, key, True))
            exportRangeAction = menu.addAction('Export range')
            exportRangeAction.triggered.connect(\
                partial(self.__exportTriggered, key, False))
            menu.exec(self.tree.viewport().mapToGlobal(point))
        except AttributeError:
            # not a device node
            return

    def __exportTriggered(self, key, complete):
        (w, b) = _wbFromKey(key)

        if (w is None) or (b is None):
            return

        self.exportDeviceHistoryRequested.emit(w, b, complete)

    def __makeDeviceNodeFont(self, node):
        font = node.font(0)
        font.setWeight(700)
        font.setPointSize(11)

        return font

    def __makeExperimentNodeFont(self, node):
        font = node.font(0)
        font.setPointSize(9)

        return font

    def __makeUnknownExperimentNodeFont(self, node):
        font = self.__makeExperimentNodeFont(node)
        font.setItalic(True)

        return font

    def __makeDeviceNode(self, key):
        (w, b) = _wbFromKey(key)
        deviceNode = QtWidgets.QTreeWidgetItem(self._root, ['W%02dB%02d' % (w+1, b+1)])
        deviceNode.setFont(0, self.__makeDeviceNodeFont(deviceNode))
        deviceNode.__setattr__('key', key)
        deviceNode.__setattr__('word', w)
        deviceNode.__setattr__('bit', b)
        self._deviceNodes[key] = deviceNode

        return deviceNode

    def __makeExperimentNode(self, parent, label, expid, path, unknown=False):
        itemNode = QtWidgets.QTreeWidgetItem(parent, [label])
        if unknown:
            itemNode.setFont(0, self.__makeUnknownExperimentNodeFont(itemNode))
        else:
            itemNode.setFont(0, self.__makeExperimentNodeFont(itemNode))
        itemNode.__setattr__('path', path)
        itemNode.__setattr__('modtag', expid)

        return itemNode

    def setTagMapper(self, mapper):
        self._tagMapper = mapper

    def loadFromStore(self, store):
        crosspoints = store.dataset('/crosspoints')
        root = self._root

        alldevkeys = sorted(crosspoints.keys())

        for key in alldevkeys:
            device = crosspoints[key]

            try:
                experiments = device['experiments']
            except KeyError:
                # no experiments done yet, skip it
                continue

            deviceNode = self.__makeDeviceNode(key)

            expkeys = sorted(experiments.keys(), key=_experimentSorter)

            for (tag, dset) in experiments.items():
                (expid, _) = tag.split('_')
                if self._tagMapper is not None:
                    try:
                        itemLabel = self._tagMapper[expid]
                        unknown = False
                    except KeyError:
                        # mark unknown modules as such
                        unknown = True
                        itemLabel = expid + ' [?]'
                else:
                    itemLabel = expid

                itemNode = self.__makeExperimentNode(deviceNode, itemLabel, \
                    expid, '%s/%s' % (experiments.name, tag), unknown)
                deviceNode.addChild(itemNode)

            root.addChild(deviceNode)

    def addExperiment(self, w, b, dsetpath):
        key = 'W%02dB%02d' % (w, b)
        path = PurePosixPath(dsetpath)
        (expid, _) = path.parts[-1].split('_')

        if key in self._deviceNodes.keys():
            deviceNode = self._deviceNodes[key]
        else:
            deviceNode = self.__makeDeviceNode(key)
            self._root.addChild(deviceNode)

        try:
            itemLabel = self._tagMapper[expid]
        except KeyError:
            itemLabel = expid

        itemNode = self.__makeExperimentNode(deviceNode, itemLabel, \
            expid, dsetpath)
        deviceNode.addChild(itemNode)

    def clear(self):
        self.tree.clear()
        self._root = QtWidgets.QTreeWidgetItem(self.tree, ['Root'])
        self.tree.setRootIndex(self.tree.indexFromItem(self._root))
        self._deviceNodes.clear()

