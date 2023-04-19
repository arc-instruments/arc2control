import abc
import json
import importlib
import functools
from collections.abc import Iterable

from PyQt6 import QtCore, QtWidgets
from .. import signals
from .. import createLogger


def modaction(key, show=True, desc=None):
    """
    This function is typically used as a decorator for actions related to
    experiment modules. The actions will typically be used to populate the
    action buttons. All module methods decorated with ``modaction`` will
    be automatically registered as actions and a button with the ``desc``
    text will be shown below their panel in the experiment tabbed widget
    (unless ``show`` is ``False``).

    :param str key: A unique identifier for this actions.
    :param bool show: Whether to show a related button in the experiment
                      panel
    :param str desc: A description for this action; this will also be used
                     as the text on the button displayed in the experiment
                     panel area.

    :raise KeyError: If a key is used twice

    .. code-block:: python

       class Experiment(BaseModule):
           # complex logic here
           # ...

           @modaction('selection', desc='Apply to Selection')
           def apply(self):
               # more complex logic here
    """

    def decorator_modaction(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            fn(*args, **kwargs)
        wrapper._is_action = True
        wrapper._action_name = key
        wrapper._action_show = show
        wrapper._action_desc = desc
        wrapper._action_target = fn
        return wrapper
    return decorator_modaction


class ActionRegister(type(QtCore.QObject)):

    def __new__(klass, name, base, dct):
        x = super(ActionRegister, klass).__new__(klass, name, base, dct)
        x._actions = {}
        for a in dir(x):
            try:
                what = getattr(x, a)
                if getattr(what, '_is_action', False):
                    if not what._action_name in x._actions:
                        x._actions[what._action_name] = \
                            (what._action_desc, what._action_target, what._action_show)
                    else:
                        raise KeyError('Key "%s" already exists' % what._action_name)
            except AttributeError as ae:
                continue
        return x


class BaseOperation(QtCore.QThread):
    """
    A standard background operation. This is what you probably need to use if
    you running a long operation using ArC2. It will connect all relevant
    signals (configuration, mapper, cell selection, etc.) and expose their
    corresponding values via properties. When a thread based on this operation
    is started the ``run`` method will be called and *must* be implemented by all
    subclasses of this class. For convenience a standard Qt signal is also
    provided which can be emitted to mark the end of the process.
    """

    operationFinished = QtCore.pyqtSignal()
    """
    Qt Signal conventionally emitted by any operation to mark that the process
    has finished.

    .. code-block:: python

       def run(self):
           # complex logic here
           # ...

           self.operationFinished.emit()
    """

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
        """
        Implement the logic of the operation by overriding this method
        """
        pass


class BaseModule(QtWidgets.QWidget, metaclass=ActionRegister):
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
        # key: object type; values: (getter fn name, setter fn name)
        self._serializableTypes = {
            QtWidgets.QLineEdit: ('text', 'setText'), \
            QtWidgets.QSpinBox: ('value', 'setValue'), \
            QtWidgets.QComboBox: ('currentIndex', 'setCurrentIndex'), \
            QtWidgets.QDoubleSpinBox: ('value', 'setValue'), \
            QtWidgets.QCheckBox: ('isChecked', 'setChecked'), \
            QtWidgets.QRadioButton: ('isChecked', 'setChecked'), \
            QtWidgets.QStackedWidget: ('currentIndex', 'setCurrentIndex'), \
            QtWidgets.QTabWidget: ('currentIndex', 'setCurrentIndex')
        }
        self._logger = createLogger(tag)

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
        Returns the appropriately formatted logger for this module. See `the
        python logging documentation for more
        <https://docs.python.org/3/library/logging.html#logging.Logger>`_.
        """
        return self._logger

    @property
    def modargs(self):
        """
        Returns a tuple containing all the necessary arguments to pass
        to a new ``BaseModule``. This is useful when trying to instantiate
        modules from within other modules. These are

        * A weak reference to the current ArC2 object, if connected
        * The current ArC2 configuration
        * The current read-out voltage
        * A weak reference to the currently opened dataset
        * The current crosbbar cell selection
        * The currently selected Channel Mapper
        """
        return ( \
            self._arc, self._arcconf, self._readoutVoltage, \
            self._datastore, self.cells, self._mapper )

    def addSerializableType(self, typ, getter, setter):
        """
        Register the setters and getters of a non standard
        widgets that should be serialized with ``toJson``.
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

    def toJson(self):
        """
        Export all the adjustable children of this module to a JSON fragment. All
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

        return json.dumps({'modname': self.fullModuleName, \
            'widgets': widgets }, indent=2)

    def toJsonFile(self, fname):
        """
        Same as :meth:`~arc2control.modules.base.BaseModule.toJson` but
        save to a file instead.

        :param str fname: The filename of the JSON file to export current
                          module's values.
        """
        with open(fname, 'w') as f:
            f.write(self.toJson())

    def fromJson(self, frag):
        """
        Load panel settings from a JSON fragment. Most common widget values are
        stored automatically but if custom widgets are present the subclass
        *must* register a setter and a getter method for the class using
        :meth:`~ar2control.modules.base.BaseModule.addSerializableType`.

        :param str frag: The JSON fragment to load from
        """
        raw = json.loads(frag)['widgets']

        for (name, attrs) in raw.items():
            try:
                klsname = attrs['type']
            except KeyError:
                continue
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

    def fromJsonFile(self, fname):
        """
        Same as :meth:`~arc2control.modules.base.BaseModule.fromJson`
        but read from a file instead.

        :param str fname: The JSON file to load from
        """
        frag = open(fname, 'r').read()
        self.fromJson(frag)

    def actions(self):
        """
        Returns actions performed by this module. The actions are discovered
        automatically if they are decorated with the decorator
        :meth:`~arc2control.modules.base.modaction`, otherwise this
        method needs to be overriden.

        Returns a dict containing all of the registered actions, eg.

        >>> module.actions()
        >>> # { 'selection': ('Apply to Selection', moduleClass.actionCallback, True) }

        Please note that if the :meth:`~arc2control.modules.base.modaction`
        decorator is used the callbacks are not bound to an object so in order
        to be called properly an instance of the object must be passed as their
        first argument.
        """
        return self._actions

    def arc2Present(self, title, error='No ArC TWO connected'):
        """
        Checks if an ArC TWO is present. If an ArC TWO cannot be
        found an additional error can be displayed.

        :param str title: Title of the error dialog. Set to ``None``
                          to suppress
        :param str error: Custom error to display; ignored if dialog
                          is suppressed
        """
        if self.arc is None:
            if title is not None:
                QtWidgets.QMessageBox.critical(self, title, error)
            return False
        return True

    def minSelection(self, title, cells=1, error='Need at least %d device(s) selected'):
        """
        Checks if at least ``cells`` are selected and displays an error
        otherwise. If selected cells are below the threshold an additional
        error can be displayed.

        :param str title: Title of the error dialog. Set to ``None``
                          to suppress
        :param int cells: Minimum number of selected cells to check for
        :param str error: Custom error to display; ignored if dialog
                          is suppressed
        """
        if len(self.cells) < cells:
            if title is not None:
                QtWidgets.QMessageBox.critical(self, title, error % cells)
            return False
        return True

    def __crossbarSelectionChanged(self, cb):
        self._selectedCells = cb

    def __arc2ConfigChanged(self, config):
        self._arcconf = config

    def __readoutVoltageChanged(self, voltage):
        self._readoutVoltage = voltage

    def __datastoreReplaced(self, storeref):
        self._datastore = storeref
