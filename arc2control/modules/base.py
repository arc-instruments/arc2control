import abc
import json
import importlib
try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

from PyQt6 import QtCore, QtWidgets
from .. import signals


class BaseOperation(QtCore.QThread):

    finished = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        if not isinstance(parent, BaseModule):
            raise TypeError("Parent is not a subclass of `BaseModule`")
        super().__init__(parent=parent)

        self.parent = parent

    @property
    def arc(self):
        return self.parent.arc

    @property
    def cells(self):
        return self.parent._selectedCells

    @property
    def mapper(self):
        return self.parent._mapper

    @property
    def arc2Config(self):
        return self.parent._arcconf

    @abc.abstractmethod
    def run(self):
        pass


class BaseModule(QtWidgets.QWidget):

    experimentFinished = QtCore.pyqtSignal(int, int, str)

    def __init__(self, arcref, arcconf, vread, store, name, tag, cells, mapper, parent=None):
        super().__init__(parent=parent)

        self.name = name
        self.tag = tag
        self._arc = arcref
        self._arcconf = arcconf
        self._readoutVoltage = vread
        self._selectedCells = cells
        self._mapper = mapper
        self._datastore = store
        self._serializableTypes = {
            #    type:, getter, setter
            QtWidgets.QLineEdit: ('text', 'setText'), \
            QtWidgets.QSpinBox: ('value', 'setValue'), \
            QtWidgets.QComboBox: ('currentIndex', 'setCurrentIndex'), \
            QtWidgets.QDoubleSpinBox: ('value', 'setValue'), \
            QtWidgets.QCheckBox: ('isChecked', 'setChecked'), \
            QtWidgets.QRadioButton: ('isChecked', 'setChecked'), \
            QtWidgets.QStackedWidget: ('currentIndex', 'setCurrentIndex'), \
            QtWidgets.QTabWidget: ('currentIndex', 'setCurrentIndex')
        }

        signals.arc2ConnectionChanged.connect(self.__arc2ConnectionChanged)
        signals.crossbarSelectionChanged.connect(self.__crossbarSelectionChanged)
        signals.arc2ConfigChanged.connect(self.__arc2ConfigChanged)
        signals.readoutVoltageChanged.connect(self.__readoutVoltageChanged)

    @property
    def arc(self):
        """
        Return a reference to the currently active ArC2 instrument, or
        None, if no connection exists
        """
        try:
            return self._arc()
        # reference points to nothing
        except TypeError:
            return None

    @property
    def cells(self):
        """
        Return the currently selected cells
        """
        return self._selectedCells

    @property
    def mapper(self):
        """
        Return the current bit/word to channel mapping configuration
        """
        return self._mapper

    @property
    def arc2Config(self):
        """
        Return the current arc2 configuration
        """
        return self._arcconf

    @property
    def readoutVoltage(self):
        return self._readoutVoltage

    def __arc2ConnectionChanged(self, connected, ref):
        if connected:
            self._arc = ref
        else:
            self._arc = None

    @property
    def fullModuleName(self):
        klass = self.__class__
        fullType = klass.__module__ + '.' + klass.__qualname__

        return fullType

    @property
    def datastore(self):
        return self._datastore

    @property
    def description(self):
        return ''

    def addSerializableType(self, typ, getter, setter):
        """
        Register the setters and getters of a non standard
        widgets that should be serialized with ``exportToJson``.
        """
        self._serializableTypes.append((typ, getter, setter))

    def exportToJson(self, fname):
        """
        Export all the adjustable children of this module to a JSON
        file. All individual widgets must set a unique name using
        `setObjectName` for this to work properly. Standard Qt
        Widgets and custom widgets that are made up from standard
        widgets are dealed with automatically. For bespoke widgets,
        these must be registered with ``self.addSerializableType``.
        """
        types = tuple(self._serializableTypes.keys())

        widgets = {}
        objs = self.findChildren(types)

        for o in objs:
            # ignore QLineEdits that are part of a QSpinBox
            if o.objectName() == 'qt_spinbox_lineedit':
                continue
            klass = o.__class__
            fullType = klass.__module__ + '.' + klass.__qualname__
            setter = self._serializableTypes[klass][1]
            getter = getattr(o, self._serializableTypes[klass][0])

            values = getter()

            if isinstance(values, str) or not isinstance(values, Iterable):
                actualValues = [values]
            else:
                actualValues = values

            widgets[o.objectName()] = {'type': fullType, \
                'setter': self._serializableTypes[klass][1],\
                'args': [*actualValues]}

        with open(fname, 'w') as f:
            f.write(json.dumps({'modname': self.fullModuleName, \
                'widgets': widgets }, indent=2))

    def loadFromJson(self, fname):
        raw = json.loads(open(fname, 'r').read())['widgets']

        for (name, attrs) in raw.items():
            klsname = attrs['type']
            setterName = attrs['setter']
            args = attrs['args']

            klsparts = klsname.split('.')
            pkg = ".".join(klsparts[:-1])

            try:
                mod = importlib.import_module(pkg)
                klass = getattr(mod, klsparts[-1])
            except TypeError:
                continue

            wdg = self.findChild(klass, name)

            setter = getattr(wdg, setterName)
            setter(*args)

    def __crossbarSelectionChanged(self, cb):
        self._selectedCells = cb

    def __arc2ConfigChanged(self, config):
        self._arcconf = config

    def __readoutVoltageChanged(self, voltage):
        self._readoutVoltage = voltage
