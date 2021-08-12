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


def main():
    realpath = os.path.dirname(os.path.realpath(__file__))
    mapfile = os.path.join(realpath, 'mappings', 'resarray32.toml')

    mapraw = toml.loads(open(mapfile).read())
    words = mapraw['config']['words']
    bits = mapraw['config']['bits']
    wordarr = mapraw['mapping']['words']
    bitarr = mapraw['mapping']['bits']
    # print("Words: %d, Bits: %d" % (words, bits))

    mapper = ChannelMapper(words, bits, wordarr, bitarr)

    # for word in range(0, words):
    #     for bit in range(0, bits):
    #         print("(W: %2d; B: %2d) → (%2d, %2d)" % \
    #             (word, bit, *mapper.wb2ch[word][bit]))

    # print("bitline ←→ channel", mapper.ch2b)
    # print("wordline ←→ channel", mapper.ch2w)

    app = QtWidgets.QApplication([])
    graphics.initialise()
    wdg = App(mapper)
    wdg.show()
    app.exec()

