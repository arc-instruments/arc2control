from PyQt6 import QtCore, QtWidgets
from arc2control.widgets.app import App
import os.path
import toml
import numpy as np
from . import graphics


class ChannelMapper:

    def __init__(self, words, bits, wordarr, bitarr):
        self._wb2ch = []
        self._ch2w = {}
        self._ch2b = {}
        self._wordarr = wordarr
        self._bitarr = bitarr
        self._nwords = words
        self._nbits = bits

        for word in range(0, words):
            wordline = []
            for bit in range(0, bits):
                wordline.append((wordarr[word], bitarr[bit]))
                self._ch2w[wordarr[word]] = word
                self._ch2b[bitarr[bit]] = bit
            self._wb2ch.append(wordline)

        # this is the order we need the values to be in
        word_act_idxes = zip(range(0, words), wordarr)
        bit_act_idxes = zip(range(0, bits), bitarr)

        # this is order ADC is sending back the channels
        word_adc_idxes = zip(range(0, words), sorted(wordarr))
        bit_adc_idxes = zip(range(0, bits), sorted(bitarr))

        w_monstrosity = zip([x[0] for x in word_adc_idxes],\
            [x[0] for x in sorted(word_act_idxes, key=lambda x: x[1])])
        self._word_adc2cb = [x[0] for x in sorted(w_monstrosity, key=lambda x: x[1])]

        b_monstrosity = zip([x[0] for x in bit_adc_idxes],\
            [x[0] for x in sorted(bit_act_idxes, key=lambda x: x[1])])
        self._bit_adc2cb = [x[0] for x in sorted(b_monstrosity, key=lambda x: x[1])]

    @property
    def wb2ch(self):
        """
        Convert a (wordline, bitline) combination to a channel pair
        """
        return self._wb2ch

    @property
    def ch2w(self):
        """
        Get the corresponding wordline of the specified channel
        """
        return self._ch2w

    @property
    def b2ch(self):
        """
        Get the corresponding channel of the specified bitline
        """
        return self._bitarr

    @property
    def w2ch(self):
        """
        Get the corresponding channel of the specified wordline
        """
        return self._wordarr

    @property
    def ch2b(self):
        """
        Get the corresponding bitline of the specified channel
        """
        return self._ch2b

    @property
    def nwords(self):
        """
        Number of wordlines
        """
        return self._nwords

    @property
    def nbits(self):
        """
        Number of bitlines
        """
        return self._nbits

    @property
    def bit_idxs(self):
        return self._bit_adc2cb

    @property
    def word_idxs(self):
        return self._word_adc2cb

    @property
    def total_devices(self):
        return self._nwords * self._nbits


def _discover_modules(path, base='arc2control.modules'):

    from pkgutil import iter_modules
    import importlib

    mods = {}

    for (finder, name, ispkg) in iter_modules(path):

        if name == 'base':
            # we don't care about the abstract base module
            continue

        loader = finder.find_module(name)
        try:
            mod = importlib.import_module('%s.%s' % (base, name))
            mods[mod.MOD_NAME] = mod.ENTRY_POINT
            print("Importing module:", mod)
        except (ModuleNotFoundError, ImportError, KeyError, AttributeError) as exc:
            # either `MOD_NAME`/`ENTRY_POINT` are not defined, module
            # does not exist (for some reason) or module contains error
            print(exc)
            continue

    return mods


def main():
    import sys
    import warnings

    warnings.filterwarnings('ignore', category=RuntimeWarning, \
        message='.*invalid value encountered in true_divide.*', \
        module='arc2control\.widgets\..*')

    warnings.filterwarnings('ignore', category=RuntimeWarning, \
        message='.*divide by zero encountered in true_divide.*', \
        module='arc2control\.widgets\..*')

    realpath = os.path.dirname(os.path.realpath(__file__))
    mapfile = os.path.join(realpath, 'mappings', 'resarray32.toml')

    mapraw = toml.loads(open(mapfile).read())
    words = mapraw['config']['words']
    bits = mapraw['config']['bits']
    wordarr = mapraw['mapping']['words']
    bitarr = mapraw['mapping']['bits']

    mapper = ChannelMapper(words, bits, wordarr, bitarr)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName('arc2control')
    graphics.initialise()

    # Try to discover modules in QStandardPaths; locateAll will
    # produce a list of standard data locations with decreasing locality
    # (and therefore decreasing priority). Our data folder *MUST* contain
    # a python package named `arc2emodules` to qualify
    paths = QtCore.QStandardPaths.locateAll(\
            QtCore.QStandardPaths.StandardLocation.AppDataLocation, \
            'arc2emodules', \
            QtCore.QStandardPaths.LocateOption.LocateDirectory)

    # check all the paths returned from `locateAll`
    for p in paths:
        # check for an `__init__.py` file to find out if this
        # folder is indeed a python package
        if os.path.exists(os.path.join(p, '__init__.py')):
            # success, add it to the path. Since we are traversing
            # the paths from higher to lower priority, paths returned
            # first will have higher priority if modules of the same
            # name exist
            sys.path.append(os.path.dirname(p))
        else:
            print("%s exists but doesn't look like a package" % p)

    # discover built-in modules first
    from . import modules as basemodmod
    mods = _discover_modules(basemodmod.__path__)

    # try to discover external modules now
    try:
        # this will only fail if there are no `arc2emodules` packages
        # found during the the loop above, there's nothing to do
        import arc2emodules as baseemodmod
        emods = _discover_modules(baseemodmod.__path__, 'arc2emodules')
    except ModuleNotFoundError:
        # no external modules
        emods = {}

    # load the app, merging all modules into a dict
    wdg = App(mapper, modules={**mods, **emods})
    wdg.show()
    app.exec()

