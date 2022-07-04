import os.path
import tomli


class ChannelMapper:
    """
    ChannelMapper deals with conversions between word/bitlines and ArC2 channel
    numbers. ArC2 channels are arbitrary and can be operated independently. In a
    typical crossbar scenario some of these channels will be allocated to high
    potential terminals (wordlines) and others to low potential terminals (bitlines).
    This class provides convenience functions to switch back and forth.

    The most typical way of loading a mapper would be through
    :meth:`~arc2control.mapper.ChannelMapper.from_toml` to read the values from
    the configuration file, rather than create the objects
    manually.

    :param int nwords: The number of wordlines
    :param int nbits: The number of bitlines
    :param wordarr: List of channels associated with wordlines 0 to ``nwords``
    :param bitarr: List of channels associated with bitlines 0 to ``nbits``
    :param str name: The name of this channel mapper

    :return: A new :class:`~arc2control.mapper.ChannelMapper`.
    """

    def __init__(self, nwords, nbits, wordarr, bitarr, name):

        self._wb2ch = []
        self._ch2w = {}
        self._ch2b = {}
        self._wordarr = wordarr
        self._bitarr = bitarr
        self._nwords = nwords
        self._nbits = nbits
        self._name = name

        for word in range(0, nwords):
            wordline = []
            for bit in range(0, nbits):
                wordline.append((wordarr[word], bitarr[bit]))
                self._ch2w[wordarr[word]] = word
                self._ch2b[bitarr[bit]] = bit
            self._wb2ch.append(wordline)

        # this is the order we need the values to be in
        word_act_idxes = zip(range(0, nwords), wordarr)
        bit_act_idxes = zip(range(0, nbits), bitarr)

        # this is order ADC is sending back the channels
        word_adc_idxes = zip(range(0, nwords), sorted(wordarr))
        bit_adc_idxes = zip(range(0, nbits), sorted(bitarr))

        w_monstrosity = zip([x[0] for x in word_adc_idxes],\
            [x[0] for x in sorted(word_act_idxes, key=lambda x: x[1])])
        self._word_adc2cb = [x[0] for x in sorted(w_monstrosity, key=lambda x: x[1])]

        b_monstrosity = zip([x[0] for x in bit_adc_idxes],\
            [x[0] for x in sorted(bit_act_idxes, key=lambda x: x[1])])
        self._bit_adc2cb = [x[0] for x in sorted(b_monstrosity, key=lambda x: x[1])]

    @property
    def name(self):
        """
        Returns the current configuration name
        """
        return self._name

    @property
    def wb2ch(self):
        """
        Convert a (wordline, bitline) combination to a channel pair

        .. code-block:: pycon

           >>> (high, low) = mapper.wb2ch[wordline][bitline]
        """
        return self._wb2ch

    @property
    def ch2w(self):
        """
        Get the corresponding wordline, if any, for the specified channel
        """
        return self._ch2w

    @property
    def b2ch(self):
        """
        Get the corresponding channel, if any, for the specified bitline
        """
        return self._bitarr

    @property
    def w2ch(self):
        """
        Get the corresponding channel, if any, for the specified wordline
        """
        return self._wordarr

    @property
    def ch2b(self):
        """
        Get the corresponding bitline, if any, for the specified channel
        """
        return self._ch2b

    @property
    def nwords(self):
        """
        Number of configured wordlines
        """
        return self._nwords

    @property
    def nbits(self):
        """
        Number of configured bitlines
        """
        return self._nbits

    @property
    def bit_idxs(self):
        """
        Indices of the bit-associated channels in the ArC2 raw response.
        Typically libarc2 reports all channels, 0 to 63, in ascending channel
        order. This property will return the channels associated with *bitlines*
        in the current configuration in *ascending bitline number order*.
        """
        return self._bit_adc2cb

    @property
    def word_idxs(self):
        """
        Indices of the word-associated channels in the ArC2 raw response.
        Typically libarc2 reports all channels, 0 to 63, in ascending channel
        order. This property will return the channels associated with *wordlines*
        in the current configuration in *ascending wordline number order*.
        """
        return self._word_adc2cb

    @property
    def total_devices(self):
        """
        Total number of configured crosspoints.
        """
        return self._nwords * self._nbits

    @staticmethod
    def from_toml(fname):
        """
        Create a new ChannelMapper from a toml configuration file.

        :param str fname: The filename of the mapper to load

        :return: A new :class:`~arc2control.mapper.ChannelMapper`.
        """
        mapraw = tomli.loads(open(fname).read())
        words = mapraw['config']['words']
        bits = mapraw['config']['bits']
        wordarr = mapraw['mapping']['words']
        bitarr = mapraw['mapping']['bits']

        try:
            name = mapraw['config']['name']
        except KeyError:
            (name, _) = os.path.splitext(os.path.basename(fname))

        return ChannelMapper(words, bits, wordarr, bitarr, name=name)
