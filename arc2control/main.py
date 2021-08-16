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


def _discover_modules(path):

    from pkgutil import iter_modules
    import importlib

    mods = {}

    for (finder, name, ispkg) in iter_modules(path):

        if name == 'base':
            # we don't care about the abstract base module
            continue

        loader = finder.find_module(name)
        mod = importlib.import_module('arc2control.modules.%s' % name)
        mods[mod.MOD_NAME] = mod.ENTRY_POINT

    return mods


def main():
    realpath = os.path.dirname(os.path.realpath(__file__))
    mapfile = os.path.join(realpath, 'mappings', 'resarray32.toml')

    mapraw = toml.loads(open(mapfile).read())
    words = mapraw['config']['words']
    bits = mapraw['config']['bits']
    wordarr = mapraw['mapping']['words']
    bitarr = mapraw['mapping']['bits']

    mapper = ChannelMapper(words, bits, wordarr, bitarr)

    from . import modules as basemodmod
    mods = _discover_modules(basemodmod.__path__)

    app = QtWidgets.QApplication([])
    graphics.initialise()
    wdg = App(mapper, modules=mods)
    wdg.show()
    app.exec()

