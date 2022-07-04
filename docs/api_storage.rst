The H5 Data Store
=================

Introduction
------------

ArC TWO Control Panel uses an HDF5-based file format to store all data. It's
a scalable, strongly-typed format with filesystem-like hierarchy, suitable for
large datasets. The ``H5DataStore`` API defines a file format on top of HDF5
with some provisions towards crossbar-oriented experiments. For all modules,
either internal or external, as well the corresponding background operations
the active datastore is exposed via the ``datastore`` property so there should
not be a reason to create a new datastore on an active ArC2Control session.


The file format
---------------

Data in HDF5 is organised in groups and datasets in a filesystem-like
hierarchy. The ArC TWO Control Panel API defines a few specific groups and
datasets that are guaranteed to be always available. Every item in an HDF5
file can contain additional metadata, or *attributes* in HDF5 lingo. Some
attributes are always defined but arbitrary attributes can be attached to a
dataset. This can be experiment-specific data or just additional metadata
for bookkeeping purposes.

A dataset or group in HDF5 can be identified by directory-like structure
such as ``/data/timeseries/alpha``. For example from this path we can
understand that dataset ``alpha`` is member of group ``timeseries``
which itself is member of group ``data`` which is a toplevel group. All
toplevel groups are implicitly members of the *root* node which is not
typically named. ArC2Control defines the following toplevel groups with
the their respective attributes.

.. list-table:: Toplevel HDF5 groups and attributes
   :widths: 30 40 15 15
   :header-rows: 1

   * - Group
     - Attribute
     - Type
     - Required?
   * - **root** (hidden)
     - H5DS_VERSION_MAJOR
     - int64
     - Y
   * -
     - H5DS_VERSION_MINOR
     - int64
     - Y
   * -
     - PYTABLES_FORMAT_VERSION
     - str128
     - N
   * - **/synthetics**
     - No attributes defined
     - N/A
     - N/A
   * - **/crosspoints**
     - No attributes defined
     - N/A
     - N/A
   * - **/crossbar**
     - words
     - int64
     - Y
   * -
     - bits
     - int64
     - Y

The */synthetics* group holds experiments that can span more than one
devices; the */crosspoints* group holds experiments groups of crosspoint
experiments in the format of ``W00B00``. A crosspoint group can hold
either a group with experiment datasets or just a single dataset. Group
*/crossbar* contains a current and voltage view of the the entire crossbar
array. Since the crossbar size is configurable the ``words`` and ``bits``
attributes must be defined.

Below is an example structure of a hypothetical data file. **G** denotes
a group and **D** a dataset.

.. code-block::


   [G] / # root node
    │
    ├── [G] synthetics # tests with more than one crosspoint, always present
    │    │
    │    ├─ [D] test00 # data, shape depending on experiment
    │    ├─ [D] test01 # data, shape depending on experiment
    |    └─ [G] test02 # experiment with more than one tables
    │        │
    │        └─ [D] test02a # experiment data
    │
    ├── [G] crosspoints # data tied to a single device
    │    │
    │    └── [G] W00B00 # crosspoint
    │         │
    │         ├─ [D] timeseries # history of device biasing
    │         │                 # current, voltage, pulse_width, read_voltage, type
    │         │                 # 5 columns, expandable length, always present
    │         │
    │         └─ [G] experiments
    │             │
    │             ├─ [D] test00 # data, shape depending on experiment
    │             ├─ [D] test01 # data, shape depending on experiment
    │             └─ [G] test02 # experiment with more than one tables
    │                 │
    │                 └─ [D] test02a # experiment data
    │
    │
    │
    └── [G] crossbar # crossbar raster view, always present
         │           # this only holds the last crossbar status
         │           # individual device history is covered by
         │           # crosspoints/WXXBYY/timeseries
         │
         ├─ [D] voltage # shape = (bits × words), always present
         └─ [D] current # shape = (bits × words), always present


The size and data type of each individual dataset is completely up to the
developer to decide. ArC2Control does not assume anything for the type of
contained data as long as their position in the file conforms to the above
specification. You should not need to create the structure manually as there
are functions that take care of the naming and structure of datasets. Below
is an example of interacting with an ``H5DataStore``. Datasets have strict
datatype requirements and as such the datatype *must* be known at creation
time. The datatype is specified as a numpy `structured array dtype`_.

.. code-block:: python

   from arc2control.h5utils import H5DataStore         # < This is done by
   import numpy as np                                  # < automatically by
                                                       # < ArC2Control
   datastore = H5DataStore('fname.h5', shape=(32, 32)) # <

   # Add a reading to a specific crosspoint, structure will be
   # created automatically
   datastore.update_status(5, 7, 1.0e-6, 0.5, 100e-6, 0.5, OpType.PULSEREAD)

   # let's create some dummy data, the columns must be equally sized
   dsetlen = 1000
   current = np.random.normal(size=(dsetlen,))
   voltage = np.random.normal(size=(dsetlen,))

   # H5DataStore used numpy dtypes to describe datasets
   dtype = [('voltage', '<f4'), ('current', '<f4')]
   # Create a new dataset for an experiment with identifier 'RET'
   dset = datastore.make_wb_table(5, 7, 'RET', (dsetlen, ), dtype)

   # broadcast the data
   dset[:, 'voltage'] = voltage
   dset[:, 'current'] = current

   # data is now saved in the dataset


A note on expandable datasets
-----------------------------

Datasets can be created in the backing store as appendable datasets. This is
not a list in the python sense but lots of chunked tables tied together
efficiently (hopefully). All expandable datasets created with this class,
including the built-in timeseries, *MUST* have an ``NROWS`` attribute that
signified the next available index. This is done automatically for methods
:meth:`~arc2control.h5utils.H5DataStore.make_wb_table` and
:meth:`~arc2control.h5utils.H5DataStore.make_synthetic_table` as well as the
datasets returned by the :meth:`~arc2control.h5utils.H5DataStore.dataset`
method.


API Reference
-------------

.. automodule:: arc2control.h5utils
    :members:

.. _`structured array dtype`: https://numpy.org/doc/stable/user/basics.rec.html
