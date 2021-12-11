import os.path
import tomli


class ChannelMapper:
    """
    ChannelMapper deals with conversions between word/bitlines and ArC2 channel
    numbers. ArC2 channels are arbitrary and can be operated independently. In a
    typical crossbar scenario some of these channels will be allocated to high
    potential terminals (wordlines) and others to low potential terminals (bitlines).
    This class provides convenience functions to switch back and forth.

    The most typical way of loading a mapper would be through `ChannelMapper.from_toml`
    to read the values from the configuration file, rather than create the objects
    manually.
    """

    def __init__(self, nwords, nbits, wordarr, bitarr, name):
        """
        Create a new Channel mapper with `nwords` wordlines and
        `nbits` bitlines. Argument `wordarr` (`bitarr`) is the list
        of channels associated with wordlines (bitlines) `0` to `nwords`
        (`0` to `nbits`) in ascending order.
        """
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
        order. This property will return the channels associated with _wordlines_
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
        Create a new ChannelMapper from a toml configuration file. The format of the
        TOML file is (example is mapping `standard32.toml` found under `mappings`).

        ```
        [config]
        # optional name for this configuration
        # if left empty will default to the filename
        name = "PLCC 32×32"
        # number of total word- and bitlines (required)
        words = 32
        bits = 32

        [mapping]
        # corresponding channels for wordlines
        # in this case wordline 0 is channel 16, wordline 1 is channel 63
        # and so on.
        words = [
            16, 63, 17, 62, 18, 61, 19, 60,
            20, 59, 21, 58, 22, 57, 23, 56,
            24, 55, 25, 54, 26, 53, 27, 52,
            28, 51, 29, 50, 30, 49, 31, 48
        ]

        # corresponding channels for bitlines
        # in this case bitline 0 is channel 15, bitline 1 is channel 32
        # and so on.
        bits = [
            15, 32, 14, 33, 13, 34, 12, 35,
            11, 36, 10, 37,  9, 38,  8, 39,
             7, 40,  6, 41,  5, 42,  4, 43,
             3, 44,  2, 45,  1, 46,  0, 47
        ]
        ```

        ArC2Control comes with some standard mappings which are always available.
        Further mappings can be added in the local data directory, typically
        `%APPDATA%\\Roaming\\arc2control\\mappings` in Windows, or
        `~/.local/share/arc2control/mappings` on Linux. Files **must** end in `.toml`
        to be loaded properly during ArC2Control startup.
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
