The Channel Mapper
==================

Introduction
------------

ArC TWO does not have any concept of crosspoints, or wordlines and bitlines.
It only exposes 64 channels that can be interconnected arbitrarily. The Channel
Mapper is used to translate between ArC TWO channels and configurable
crosspoints.  Since there are many different requirements for channel
configurations the mapping system is fully configurable to provide different
ways to connect channels together. ArC2Control comes with a set of default
mappers for common scenarios, but new mappers can be created. This is typically
in the form of a simple TOML file that describes which channels are associated
to specific bitlines or wordlines. For example this is mapping ``standard32.toml``
that's included in ArC2Control installation.

.. code-block:: toml

   [config]
   # optional name for this configuration
   # if left empty will default to the filename
   name = "PLCC 32×32"
   # number of total word- and bitlines (required)
   words = 32
   bits = 32
   # optional list of masked crosspoints. If this
   # key is set only the specified word/bitlines
   # will be available in the crossbar view. This
   # example enables every other crosspoint along
   # the main diagonal
   mask = [
     [ 0,  0], [ 2,  2], [ 4,  4], [ 6,  6],
     [ 8,  8], [10, 10], [12, 12], [14, 14],
     [16, 16], [18, 18], [20, 20], [22, 22],
     [24, 24], [26, 26], [28, 28], [30, 30]
   ]

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


Using the mapper
----------------

Within the context of an ArC2Control session you should not need to instantiate
mappers manually. The currently active mapper will always be available from the
``mapper`` property of the current module or long-running operation. Changes to
the mapper are automatically propagated to modules. In order to do anything
with ArC TWO you first need to convert the currently active crosspoint
coordinates to the correct channel pair. This is usually done using the
readonly :attr:`~arc2control.mapper.ChannelMapper.wb2ch` dict property that
does the translation. For instance this is an abridged snippet from the
curvetracer module that ships with ArC TWO.

.. code-block:: python

   def do_ramp(self, w, b, *args):

       # convert wordline w and bitline b to a corresponding (high/low)
       # ArC TWO channel pair
       (high, low) = self.mapper.wb2ch[w][b]

       # this can then be used to do ArC TWO operations
       # reminder: self.arc is always defined within modules
       self.arc.generate_ramp(high, low, *args)


Adding more mappings
--------------------

ArC2Control comes with some standard mappings which are always
available.  Further mappings can be added in the local data directory,
typically ``%APPDATA%\Roaming\arc2control\mappings`` in Windows, or
``~/.local/share/arc2control/mappings`` on Linux. Files **must** end in
``.toml`` to be loaded properly during ArC2Control startup.


API Reference
-------------

.. automodule:: arc2control.mapper
    :members:
