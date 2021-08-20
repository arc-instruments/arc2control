from PyQt6 import QtCore, QtWidgets


def _experimentSorter(item):
    (tag, tstamp) = item.split('_')
    return int(tstamp)


class DeviceExplorerWidget(QtWidgets.QWidget):

    #                                      tag, path
    experimentSelected = QtCore.pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)

        self._root = QtWidgets.QTreeWidgetItem(self.tree, ['Root'])
        self._deviceNodes = {}
        self._tagMapper = None
        self.tree.setRootIndex(self.tree.indexFromItem(self._root))
        self.tree.itemDoubleClicked.connect(self.__itemSelected)

        self.layout.addWidget(self.tree)

    def __itemSelected(self, item, _):
        if item.parent() == self._root:
            return

        self.experimentSelected.emit(item.modtag, item.path)

    def __makeDeviceNodeFont(self, node):
        font = node.font(0)
        font.setWeight(700)
        font.setPointSize(11)

        return font

    def __makeExperimentNodeFont(self, node):
        font = node.font(0)
        font.setPointSize(9)

        return font

    def setTagMapper(self, mapper):
        self._tagMapper = mapper

    def loadFromStore(self, store):
        crosspoints = store.dataset('/crosspoints')
        root = self._root

        alldevkeys = sorted(crosspoints.keys())

        for key in alldevkeys:
            device = crosspoints[key]
            deviceNode = QtWidgets.QTreeWidgetItem(root, [key])
            deviceNode.setFont(0, self.__makeDeviceNodeFont(deviceNode))
            deviceNode.__setattr__('key', key)

            experiments = device['experiments']
            expkeys = sorted(experiments.keys(), key=_experimentSorter)

            for (tag, dset) in experiments.items():
                (expid, _) = tag.split('_')
                if self._tagMapper is not None:
                    try:
                        itemLabel = self._tagMapper[expid]
                    except KeyError:
                        itemLabel = expid
                else:
                    itemLabel = expid

                itemNode = QtWidgets.QTreeWidgetItem(deviceNode, [itemLabel])
                itemNode.setFont(0, self.__makeExperimentNodeFont(itemNode))
                itemNode.__setattr__('path', '%s/%s' % (experiments.name, tag))
                itemNode.__setattr__('modtag', expid)
                deviceNode.addChild(itemNode)

            self._deviceNodes[key] = deviceNode
            root.addChild(deviceNode)

    def clear(self):
        self.tree.clear()
        self._root = QtWidgets.QTreeWidgetItem(self.tree, ['Root'])
        self.tree.setRootIndex(self.tree.indexFromItem(self._root))
        self._deviceNodes.clear()

