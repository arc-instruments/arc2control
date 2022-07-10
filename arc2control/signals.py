"""
During ArC2Control startup a set of `Qt signals`_ will be initialised. These
are used to pass messages between the UI and various constituent components as
well as internal and external modules. Current set of signals includes arc2
status changes (connection and configuration) as well as data updates to be
propagated to the UI. Modules can connect and trigger all modules here although
practically connection and configuration signals need not be triggered
explicitly. If you are subclassing :class:`~arc2control.modules.base.BaseModule`
then all the required signals are preconnected and the values they correspond
to are exposed directly as object properties or methods. You can still connect
to them but it's not recommended to emit them explicitly.

To trigger a signal call its ``emit`` method with the correct configuration
of arguments (see *Signature* on each signal for details).

.. _`Qt signals`: https://www.riverbankcomputing.com/static/Docs/PyQt6/signals_slots.html
"""

from PyQt6.QtCore import QObject, pyqtSignal
from .h5utils import OpType
from numpy import ndarray, array


class __Signals(QObject):
    # status changes
    arc2ConnectionChanged = pyqtSignal(bool, object)
    arc2ConfigChanged = pyqtSignal(object)
    crossbarSelectionChanged = pyqtSignal(set)
    readoutVoltageChanged = pyqtSignal(float)

    # value updates
    # wordline, bitline, current, voltage, pulse width, vread, optype
    valueUpdate = pyqtSignal(int, int, float, float, float, float, OpType)
    # same, but with ndarrays for bulk updates
    valueBulkUpdate = pyqtSignal(int, int, ndarray, ndarray, ndarray, ndarray, ndarray)
    # wordline, bitline
    dataDisplayUpdate = pyqtSignal(int, int)
    # weakref to the current dataset
    datastoreReplaced = pyqtSignal(object)


__signals = __Signals()


arc2ConnectionChanged = __signals.arc2ConnectionChanged
"""
Current connection to ArC2 changed. This means that an instrument has been
connected or disconnected.

Signature: ``arc2ConnectionChanged(connected: bool, arc: weakref(pyarc2.Instrument), /)``
"""

arc2ConfigChanged = __signals.arc2ConfigChanged
"""
Current ArC2 configuration changed. This typically means that either idle mode or
default connection configuration (ground or idle) has changed.

.. caution::
   It's not recommended to emit this signal from modules.

Signature: ``arc2ConfigChanged(status: bool, arc: pyarc2.ArC2Config, /)``
"""

crossbarSelectionChanged = __signals.crossbarSelectionChanged
"""
Current crosspoint selection changed. This is typically emitted after a user
selected a different set of crosspoints. Please not that this is *not*
triggered when the same devices have been selected.

.. caution::
   It's not recommended to emit this signal from modules.

Signature: ``crossbarSelectionChanged(selection: set)``
"""

readoutVoltageChanged = __signals.readoutVoltageChanged
"""
Selected read-out voltage changed. This is emitted when the global read-out
voltage has been altered.

.. caution::
   It's not recommended to emit this signal from modules, unluess you want
   to change the global read-out voltage (which is, of course, not
   recommended).

Signature: ``readoutVoltageChanged(voltage: float)``
"""

valueUpdate = __signals.valueUpdate
"""
Specified crosspoint status changed (single update). Emit this signal to
store a value in the timeseries data of the selected crosspoint.

Signature: ``valueUpdate(word: int, bit: int, current: float, vpulse: float, pulse_width: float,
vread: float, optype: arc2control.h5utils.OpType)``
"""

valueBulkUpdate = __signals.valueBulkUpdate
"""
Specified crosspoint status changed (multiple values). Emit this signal to store
multiple values in the timeseries data of the selected crosspoint.

Signature: ``valueUpdate(word: int, bit: int, current: ndarray, vpulse: ndarray,
pulse_width: ndarray, vread: ndarray, optype: ndarray)``
"""

dataDisplayUpdate = __signals.dataDisplayUpdate
"""
Data display update request on specific crosspoint. Emit this signal to
request a plot update for the specific crosspoint. Note that this operation is
independent of the data storage facility that is triggered by the `valueUpdate`
and `valueBulkUpdate` signals. When doing fast operation it's recommended that
you cap your data display update requests to about 5-10 per second otherwise
delays will be incurred.

Signature: ``dataDisplayUpdate(word: int, bit: int)``
"""

datastoreReplaced = __signals.datastoreReplaced
"""
The current HDF5 datast has been replaced with a new one. This signal should
only really be used internally and it's triggered when a new dataset is
opened or when a new dataset is created

Signature: ``datastoreReplaced(dataset: weakref)``
"""
