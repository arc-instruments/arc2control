import abc
import json
import importlib
import logging
try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

from PyQt6 import QtCore, QtWidgets
from .. import signals


class BaseOperation(QtCore.QThread):
    """
    A standard background operation. This is what you probably need to use if
    you running a long operation using ArC2. It will connect all relevant
    signals (configuration, mapper, cell selection, etc.) and expose their
    corresponding values via properties. When a thread based on this operation
    is started the ``run`` method will be called and *must* be implemented by all
    subclasses of this class.
    """

    finished = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        if not isinstance(parent, BaseModule):
            raise TypeError("Parent is not a subclass of `BaseModule`")
        super().__init__(parent=parent)

        self._logger = parent.logger
        self.parent = parent

    @property
    def arc(self):
        """
        Reference to the currently connected ArC2 instrument (if any)
        """
        return self.parent.arc

    @property
    def cells(self):
        """
        A set of tuples representing the currently selected crosspoints
        `(word, bit)`.
        """
        return self.parent._selectedCells

    @property
    def mapper(self):
        """
        The currently activated channel mapper (see :class:`~arc2control.mapper.ChannelMapper`).
        """
        return self.parent._mapper

    @property
    def arc2Config(self):
        """
        The currently enabled ArC2 configuration
        """
        return self.parent._arcconf

    @property
    def logger(self):
        """
        Returns the appropriately format logger for this module. See `the
        python logging documentation for more
        <https://docs.python.org/3/library/logging.html#logging.Logger>`_.
        """
        return self._logger

    @abc.abstractmethod
    def run(self):
        pass


class BaseModule(QtWidgets.QWidget):
    """
    Base Module for all ArC2Control plugins. A valid ArC2 plugin _MUST_ derive
    from this class to be properly loaded on startup. The base class will track
    all UI and instrument changes and exposes the relevant values via properies
    and methods. The constructor for the module will be typically called with
    the correct arguments when the user clicks the "Add" button on the experiment
    panel of ArC2Control

    :param arcref: A reference to the currently connected ArC TWO
    :param arcconf: The current ArC TWO configuration
    :param vread: Currently configured read voltage
    :param store: A reference to the currently opened datastore
    :param name: The name of this module
    :param tag: A short tag desribing this module
    :param cells: A reference to the current crosspoint selection
    :param mapper: A reference to the current channel mapper
    """

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
        self._logger = logging.getLogger(tag)

        signals.arc2ConnectionChanged.connect(self.__arc2ConnectionChanged)
        signals.crossbarSelectionChanged.connect(self.__crossbarSelectionChanged)
        signals.arc2ConfigChanged.connect(self.__arc2ConfigChanged)
        signals.readoutVoltageChanged.connect(self.__readoutVoltageChanged)
        signals.datastoreReplaced.connect(self.__datastoreReplaced)

    @property
    def arc(self):
        """
        A reference to the currently active ArC TWO instrument, or None, if no
        connection exists
        """
        try:
            return self._arc()
        # reference points to nothing
        except TypeError:
            return None

    @property
    def cells(self):
        """
        The currently selected cells
        """
        return self._selectedCells

    @property
    def mapper(self):
        """
        The current bit/word to channel mapping configuration
        """
        return self._mapper

    @property
    def arc2Config(self):
        """
        The current ArC TWO configuration
        """
        return self._arcconf

    @property
    def readoutVoltage(self):
        """
        The active read-out voltage
        """
        return self._readoutVoltage

    def __arc2ConnectionChanged(self, connected, ref):
        if connected:
            self._arc = ref
        else:
            self._arc = None

    @property
    def fullModuleName(self):
        """
        The fully qualified python class name
        """
        klass = self.__class__
        fullType = klass.__module__ + '.' + klass.__qualname__

        return fullType

    @property
    def datastore(self):
        """
        A reference to the current datastore. See :class:`~arc2control.h5utils.H5DataStore`.
        """
        return self._datastore()

    @property
    def description(self):
        """
        Description of the operation of this module. This is typically displayed under
        the panel name in the main ArC2Control UI. Subclasses must implement this if
        they need to have a description visible (by default it's empty).
        """
        return ''

    @property
    def logger(self):
        """
        Returns the appropriately format logger for this module. See `the
        python logging documentation for more
        <https://docs.python.org/3/library/logging.html#logging.Logger>`_.
        """
        return self._logger

    def addSerializableType(self, typ, getter, setter):
        """
        Register the setters and getters of a non standard
        widgets that should be serialized with ``exportToJson``.
        Typically ``typ`` would be a custom widget and ``setter`` and
        ``getter`` are functions of that custom widget that load and
        set its state. Custom widgets must be registered with this
        function in order to be properly serialised to and retrieved
        from a file.

        :param typ: The widget Python type
        :param getter: The ``get`` function to retrieve its value
        :param setter: The ``set`` function to set its value
        """
        self._serializableTypes.append((typ, getter, setter))

    def exportToJson(self, fname):
        """
        Export all the adjustable children of this module to a JSON file. All
        individual widgets must set a unique name using ``setObjectName`` for
        this to work properly. Standard Qt Widgets and custom widgets that are
        made up from standard widgets are dealed with automatically. For
        bespoke widgets, these must be registered with
        :meth:`~arc2control.modules.base.BaseModule.addSerializableType`.

        :param str fname: The filename of the JSON file to export current
                          module's values.
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
        """
        Load panel settings from a JSON file. Most common widget values are
        stored automatically but if custom widgets are present the subclass
        *must* register a setter and a getter method for the class using
        :meth:`~ar2control.modules.base.BaseModule.addSerializableType`.

        :param str fname: The filename to load values from
        """
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

    def __datastoreReplaced(self, storeref):
        self._datastore = storeref
