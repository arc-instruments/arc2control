import numpy as np
import h5py
from pathlib import PosixPath
import os.path
import types
import time
import math
from enum import Enum, IntEnum


_H5DS_VERSION_MAJOR = 0
_H5DS_VERSION_MINOR = 2


class H5Mode(Enum):
    READ = 'r'
    WRITE = 'w'
    APPEND = 'a'
    READEX = 'r+'


class OpType(IntEnum):
    READ      =  0b01
    PULSE     =  0b10
    PULSEREAD =  0b11


class H5AccessError(Exception):
    pass

class H5DimsError(Exception):
    pass

class H5FormatError(Exception):
    pass


def _dataset_append(dset, row):
    # this is a convenience method for chunked datasets that are created
    # with 'None' as maxshape. H5PY lacks an append function for datasets
    # so this one can be monkey-patched into datasets returned by H5DataStore
    # this needs an attribute that tracks the last inserted row. There is
    # no provision on removing rows as this is mostly needed for write-once
    # datasets
    idx = dset.attrs['NROWS']
    dset[idx] = row
    dset.attrs['NROWS'] = idx + 1


class H5DataStore:
    """
    ## HDF5 format description.

    ### Attributes
           root node: H5DS_VERSION_MAJOR: int64 (mandatory)
                      H5DS_VERSION_MINOR: int64 (mandatory)
                      PYTABLES_FORMAT_VERSION: str128
                                               (optional; for vitables compat)
                      words: int64 (mandatory)
                      bits: int64 (mandatory)
                      TITLE: str256 (optional; user-provided, defaults to fname)
     synthetics node: none
    crosspoints node: none
       crossbar node: words: int64 (mandatory)
                      bits: int64 (mandatory)

     synthetic tests: crosspoints: [int64]; shape=(crosspoints, 2) (mandatory)
                                                                │
                                                                └─ (bit, word)
    crosspoint tests: crosspoints: [int64]; shape=(1, 2) (mandatory)
                                                      │
                                                      └─ (bit, word)
     crossbar leaves: none

    ### File structure

    Format of the HDF backing store as of v0.2 (G: Group, D: Dataset)

    ```
    [G] / # root node; always present (duh!)
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
    ```

    ### Note on expandable datasets

    Datasets can be created in the backing store as appendable datasets. This is
    not a list in the python sense but lots of chunked tables tied together
    efficiently (hopefully). All expandable datasets created with this class,
    including the built-in timeseries, *MUST* have an `NROWS` attribute that
    signified the next available index. This is done automatically for methods
    `make_wb_table` and `make_synthetic_table` as well as the datasets returned
    by the `dataset` methods.
    """

    _TSERIES_DTYPE=[
        ('current', '<f4'),
        ('voltage', '<f4'),
        ('pulse_width', '<f4'),
        ('read_voltage', '<f4'),
        ('op_type', '<u4')]

    _BASE_SIZE = 1000

    def __init__(self, fname, name=None, mode=H5Mode.APPEND, shape=(32, 32)):
        """
        Create a new data store backed by file `fname`. A name can be provided
        but will default to `basename(fname)` if none is provided. When creating
        a new file with ``H5Mode.WRITE`` the crossbar dimensions must be specified
        and they default to 32×32. In append and read modes the size is picked up
        from the metadata of the file itself.

        An ``H5DataStore`` can also be used as a context manager for brief
        interactions with data files

        >>> from h5utils import H5DataStore
        >>> with H5DataStore('/path/to/store', 'dataset') as ds:
        >>>     ds.update_status(0, 0, 10e-6, 1.0, 100e-6, 0.2)
        >>> # file is saved here
        """
        self._fname = fname
        if name is None:
            name = os.path.basename(fname)

        self._h5 = h5py.File(fname, mode.value)

        # create file structure if it's a new file
        if mode == H5Mode.WRITE and self._h5.mode == H5Mode.READEX.value:
            self.__create_structure(shape, name)
        # if not (append/read) check if file structure is correct
        else:
            self.__fsck(fname)

    def __fsck(self, fname):
        attrs = self._h5.attrs
        bname = os.path.basename(fname)

        # check first if suitable versions are provided
        for key in ['PYTABLES_FORMAT_VERSION', 'H5DS_VERSION_MAJOR', 'H5DS_VERSION_MINOR']:
            if key not in attrs.keys():
                raise H5FormatError('File %s does not specify a file format version' %\
                    bname)

        # check if basic groups are there
        for grp in ['crossbar', 'crosspoints', 'synthetics']:
            if grp not in self._h5.keys():
                raise H5FormatError('File %s is missing root base group %s' %\
                    (bname, grp))

        # check if wordlines, bitlines are specified both in the
        # h5 attrs and crossbar attrs
        for key in ['words', 'bits']:
            if key not in attrs.keys():
                raise H5FormatError('File %s does not provide crossbar dimensions' %\
                    bname)
            if key not in self._h5['crossbar'].attrs.keys():
                raise H5FormatError('File %s does not provide crossbar dimensions' %\
                    bname)

    # the base HDF structure
    def __create_structure(self, shape, name):
        if self._h5.mode == H5Mode.READ.value:
            raise H5AccessError('File is opened read-only')

        self._h5.attrs['CLASS'] = 'GROUP'
        self._h5.attrs['PYTABLES_FORMAT_VERSION'] = '2.1'
        self._h5.attrs['H5DS_VERSION_MAJOR'] = _H5DS_VERSION_MAJOR
        self._h5.attrs['H5DS_VERSION_MINOR'] = _H5DS_VERSION_MINOR
        self._h5.attrs['TITLE'] = name

        self._h5.attrs['words'] = shape[0]
        self._h5.attrs['bits'] = shape[1]

        for grp in ['crossbar', 'crosspoints', 'synthetics']:
            self.__create_top_level_group(grp)

        for dset in ['voltage', 'current']:
            if dset not in self._h5['crossbar'].keys():
                self._h5['crossbar'].create_dataset(dset,
                    shape=shape, dtype=np.float32)

        self._h5['crossbar'].attrs['words'] = shape[0]
        self._h5['crossbar'].attrs['bits'] = shape[1]

    def __create_top_level_group(self, name):
        try:
            grp = self._h5.create_group(name)
            grp.attrs['CLASS'] = 'GROUP'
        except ValueError:
            # group exists, it's probably ok
            pass

    @property
    def fname(self):
        """
        Return the filename associated with this data store
        """
        return self._fname

    @property
    def name(self):
        """
        Return the name associated with this data store
        """
        try:
            return self._h5.attrs['TITLE']
        except KeyError:
            return None

    @name.setter
    def set_name(self, name):
        """
        Change the name of this data store. This is _not_ the filename
        but the internal name of the dataset for identification purposes.
        """
        self._h5.attrs['TITLE'] = name

    def close(self):
        """
        Close the file. It needs to be reopened again for any other
        interaction.
        """
        self._h5.flush()
        self._h5.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._h5.flush()
        self._h5.close()

    def __getitem__(self, key):
        return self.dataset(key)

    @property
    def current(self):
        """
        Current view of the crossbar raster
        """
        return self._h5['crossbar']['current'][:]

    @property
    def voltage(self):
        """
        Voltage view of the crossbar raster
        """
        return self._h5['crossbar']['voltage'][:]

    @property
    def resistance(self):
        """
        Resistance view of the crossbar raster
        """
        return np.abs(self.voltage/self.current)

    @property
    def conductance(self):
        """
        Conductance view of the crossbar raster
        """
        return np.abs(self.current/self.voltage)

    @property
    def shape(self):
        """
        Size of the crossbar stored in this data store
        """
        attrs = self._h5.attrs
        return (attrs['words'], attrs['bits'])

    def keys(self):
        """
        Return all top-level keys of this dataset
        """
        return self._h5.keys()

    def __create_timeseries(self, word, bit):
        grp_name = 'W%02dB%02d' % (word, bit)
        if grp_name not in self._h5['crosspoints']:
            grp = self._h5['crosspoints'].create_group(grp_name)
            dset = grp.create_dataset('timeseries', shape=(H5DataStore._BASE_SIZE,),
                dtype=self._TSERIES_DTYPE,
                maxshape=(None,), chunks=True)
            dset.attrs['NROWS'] = 0
            dset.attrs['TITLE'] = 'W%02dB%02d' % (word, bit)
            dset.attrs['CLASS'] = 'TABLE'
            dset.attrs['BASE_SIZE'] = H5DataStore._BASE_SIZE

    def timeseries(self, word, bit):
        """
        Complete biasing history of specified crosspoint
        """
        grp_name = 'W%02dB%02d' % (word, bit)
        crosspoint = self._h5['crosspoints'][grp_name]
        rows = crosspoint['timeseries'].attrs['NROWS']
        dset = crosspoint['timeseries'][0:rows]
        return dset

    def update_status(self, word, bit, current, voltage, pulse, read_voltage, optype=OpType.READ):
        """
        Add a new biasing history entry for the specified crosspoint.
        """
        # this will do nothing if timeseries already exists
        self.__create_timeseries(word, bit)
        wbid = 'W%02dB%02d' % (word, bit)

        # update the timeseries
        dset = self._h5['crosspoints'][wbid]['timeseries']
        idx = dset.attrs['NROWS']

        try:
            dset[idx] = (current, voltage, pulse, read_voltage, optype)
        except IndexError:
            # resize and try again
            dset.resize((2*dset.shape[0], ))
            dset[idx] = (current, voltage, pulse, read_voltage, optype)

        dset.attrs['NROWS'] = idx + 1

        # and the crossbar raster
        self._h5['crossbar']['current'][bit,word] = current
        self._h5['crossbar']['voltage'][bit,word] = voltage

    def update_status_bulk(self, word, bit, currents, voltages, pulses, read_voltages, optypes):
        """
        Similar to ``update_status`` but with bulk insertion of values. All parameters must
        be equally sized numpy arrays. Arguments ``read_voltages`` and ``optypes`` can be
        scalar and their values will be brodcasted over the relevant rows
        """

        self.__create_timeseries(word, bit)
        wbid = 'W%02dB%02d' % (word, bit)

        dlen = len(currents)
        for a in [voltages, pulses]:
            if len(a) != dlen:
                raise ValueError("""Currents, Voltages and Pulse Widths must have the same """
                                 """length when bulk inserting data""")

        # if len(read_voltages) is 1 and dlen > 1, ensure
        # read_voltages is a scalar to be properly broadcasted
        try:
            if dlen > 1 and len(read_voltages) == 1:
                read_voltages = read_voltages[0]
        except TypeError:
            # scalars do not have __len__
            pass

        # same with optypes
        try:
            if dlen > 1 and len(optypes) == 1:
                optypes = optypes[0]
        except TypeError:
            # scalars do not have __len__
            pass


        dset = self._h5['crosspoints'][wbid]['timeseries']
        idx = dset.attrs['NROWS']

        # check if we can fit the data in the dataset
        free_rows = dset.shape[0] - idx
        if free_rows < dlen:
            try:
                BASE_SIZE = dset.attrs['BASE_SIZE']
            except (KeyError, IndexError):
                BASE_SIZE = H5DataStore._BASE_SIZE
            # resize dataset to fit, we need at least this many
            # total rows
            min_length = idx + free_rows + 1
            # we need to double the size this many times to fit
            # the data
            factor = math.ceil(math.log(min_length/BASE_SIZE, 2))
            dset.resize((BASE_SIZE*2**factor,))

        dset[idx:idx+dlen, 'current'] = currents
        dset[idx:idx+dlen, 'voltage'] = voltages
        dset[idx:idx+dlen, 'pulse_width'] = pulses
        dset[idx:idx+dlen, 'read_voltage'] = read_voltages
        dset[idx:idx+dlen, 'op_type'] = optypes

        dset.attrs['NROWS'] = idx + dlen

        self._h5['crossbar']['current'][bit, word] = currents[-1]
        try:
            self._h5['crossbar']['voltage'][bit, word] = read_voltages[-1]
        except TypeError: # read_voltages is probably a scalar
            self._h5['crossbar']['voltage'][bit, word] = read_voltages

    def __make_group(self, crosspoints, grpname, ts=None):

        # make sure individual time series exists
        for (w, b) in crosspoints:
            try:
                self.__create_timeseries(w, b)
            except ValueError:
                # exists already, no problem
                continue

        grp = self._h5.create_group(grpname)

        if ts:
            grp.attrs['TSTAMP'] = ts

        grp.attrs['crosspoints'] = crosspoints
        grp.attrs['CLASS'] = 'GROUP'

        return grp

    def __sanitise_group_basepath(self, grp, anchor):
        if isinstance(grp, h5py.Group):
            grpname = grp.name + '/'
        elif isinstance(grp, str):
            if not grp.endswith('/'):
                grpname = grp + '/'
            else:
                grpname = grp
        else:
            raise TypeError('Group must be an instance of h5py.Group or str')

        # some sanity checks
        # first convert into a forward slash separated path (PosixPath)
        pbasepath = PosixPath(grpname)
        if pbasepath == PosixPath('/'):
            raise KeyError('Cannot attach experiment to root node')

        # then check if it's an absolute path if yes, then check
        # if the parent path is correct
        if pbasepath.anchor == '/':
            parent = pbasepath.parent
            if parent != PosixPath(anchor):
                raise KeyError('Attempting to attach experiment to wrong group node: ' \
                    + basepath)
            basepath = str(pbasepath)
        # otherwise treat the path as relative to the correct node
        else:
            basepath = '%s/%s' % (anchor, grpname)

        return basepath

    def make_wb_group(self, word, bit, name, tstamp=True):
        """
        Create a new experiment group tied to a specific crosspoint. This can be
        used to group multiple data tables under a single experimental node. This
        will return the underlying HDF group. Unless `tstamp` is set to `False`
        the current timestamp with ns precision will be added to the group name.
        """

        if tstamp:
            ts = time.time_ns()
            grpname = 'crosspoints/W%02dB%02d/experiments/%s_%d' % \
                (word, bit, name, ts)
        else:
            ts = None
            grpname = 'crosspoints/W%02dB%02d/experiments/%s' % \
                (word, bit, name)

        return self.__make_group([[word, bit]], grpname, ts)

    def make_wb_table(self, word, bit, name, shape, dtype, grp=None, maxshape=None, tstamp=True):
        """
        Create a new experiment table tied to a specific crosspoint. Arguments
        `shape` and `dtype` follow numpy conventions. This will return the
        underlying HDF dataset. If `maxshape` is `None` the dataset will
        always be chunked but will allow appends (default). Unless `tstamp` is set
        to `False` the current timestamp with ns precision will be added to the
        dataset names. If `grp` is specified then the table will be created as
        a child of the specified experiment group. Group name can be either
        relative (no leading '/') or absolute. In the latter case the parent path
        must match the corrent word/bit coordinate otherwise an exception will
        be raised. Group can either be an instance of `h5py.Group` or `str`.
        """
        # make sure time series exists
        try:
            self.__create_timeseries(word, bit)
        except ValueError:
            # exists already, no problem
            pass

        anchor = '/crosspoints/W%02dB%02d/experiments' % (word, bit)

        # if a group is specified, attach the dataset under the
        # experiment group
        if grp is not None:
            basepath = self.__sanitise_group_basepath(grp, anchor)

        # else put it under "experiments"
        else:
            basepath = anchor

        if tstamp:
            ts = time.time_ns()
            dsetname = '%s/%s_%d' % \
                (basepath, name, ts)
        else:
            dsetname = '%s/%s' % \
                (basepath, name)

        dset = self.__make_table(dsetname, shape, dtype, maxshape)

        if tstamp:
            dset.attrs['TSTAMP'] = ts

        dset.attrs['crosspoints'] = [[word, bit]]
        dset.attrs['BASE_SIZE'] = shape[0]

        return dset

    def make_synthetic_group(self, crosspoints, name, tstamp=True):
        """
        Create a new synthetic experiment group. This can be used to group
        multiple data tables under a single experimental node. This will return
        the underlying HDF group. Unless `tstamp` is set to `False` the current
        timestamp with ns precision will be added to the group name.
        """

        if tstamp:
            ts = time.time_ns()
            grpname = 'synthetics/%s_%d' % (name, ts)
        else:
            ts = None
            grpname = 'synthetics/%s' % name

        return self.__make_group(crosspoints, grpname, ts)

    def make_synthetic_table(self, crosspoints, name, shape, dtype, grp=None, maxshape=None, tstamp=True):
        """
        Create a new experiment table encompassing many crosspoints. Arguments
        `shape` and `dtype` follow numpy conventions. This will return the
        underlying HDF dataset. If `maxshape` is `None` the dataset will
        always be chunked but will allow appends (default). Unless `tstamp` is set
        to `False` the current timestamp with ns precision will be added to the
        dataset names. If `grp` is specified then the table will be created as
        a child of the specified experiment group. Group name can be either
        relative (no leading '/') or absolute. In the latter case the parent path
        must match the corrent word/bit coordinate otherwise an exception will
        be raised. Group can either be an instance of `h5py.Group` or `str`.
        """
        # make sure individual time series exists
        for (w, b) in crosspoints:
            try:
                self.__create_timeseries(w, b)
            except ValueError:
                # exists already, no problem
                continue

        anchor = '/synthetics'

        # if a group is specified, ensure it's under the correct
        # base group
        if grp is not None:
            basepath = self.__sanitise_group_basepath(grp, anchor)
        # else put it under "synthetics" as usual
        else:
            basepath = anchor

        if tstamp:
            ts = time.time_ns()
            dsetname = '%s/%s_%d' % (basepath, name, ts)
        else:
            dsetname = '%s/%s' % (basepath, name)

        dset = self.__make_table(dsetname, shape, dtype, maxshape)

        dset.attrs['crosspoints'] = [[x[0], x[1]] for x in crosspoints]
        dset.attrs['BASE_SIZE'] = shape[0]

        if tstamp:
            dset.attrs['TSTAMP'] = ts

        return dset

    def __make_table(self, name, shape, dtype, maxshape):
        if maxshape is None:
            dset = self._h5.create_dataset(name, shape=shape, dtype=dtype)
        else:
            dset = self._h5.create_dataset(name, shape=shape, dtype=dtype,
                maxshape=maxshape, chunks=True)

        dset.attrs['NROWS'] = 0
        dset.attrs['TITLE'] = name
        dset.attrs['CLASS'] = 'TABLE'

        # add an append function
        dset.append = types.MethodType(_dataset_append, dset)

        return dset

    def dataset(self, name):

        dset = self._h5[name]
        dset.append = types.MethodType(_dataset_append, dset)

        return dset

