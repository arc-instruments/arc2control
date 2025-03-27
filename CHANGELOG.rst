Changelog
=========

.. _v0-2-0:

`0.2.0`_ — 2025-03-27
~~~~~~~~~~~~~~~~~~~~~

This is the second release of ArC TWO Control. It fixes a lot of bugs and adds
new functionality.

* Brand new AutoFormer module for feedback-based electroforming
* Can now open datasets as read-only for analysis and data removal
* Faster loading of data tables by using the actual HDF5 datasets as backing models
* Configurable IO setup per mapper/daughterboard
* Added channel mappings for standalone CQFJ packages (passive array)
* A list of recent datasets is now available under the File menu
* Automatic compilation of Qt UI files for built-in and user-provided modules
* Better logging facilities
* Fixed a but when accessing HDF5 dataset properties
* HDF5 datasets now support grouped experiemnts (ie. more than one dataset per experiment)
* Minimize spurious warnings related to plotting
* Drop support for Python < 3.8

.. _`0.2.0`: https://github.com/arc-instruments/arc2control/releases/tag/0.2.0

.. _v0-1-0:

`0.1.0`_ — 2022-08-06
~~~~~~~~~~~~~~~~~~~~~

This is the initial somewhat functional release of ArC2Control. Bugs are still
to be expected. Aim is to present a stable API for further module development
and expose some of the functionality of ArC TWO. Highlights of this initial
release are

* Initial version of the HDF5-based format for data storage and retrieval
* Firmware management tool
* First version of the public module API - built-in modules use the same public
  API
* Two built-in modules: CurveTracer and Retention
* Manual pulse and read operations
* Full or reduced (masked) crossbar support
* Flexible channel mappers
* Adjustable plot displays for Current, Resistance or Conductance

.. _`0.1.0`: https://github.com/arc-instruments/arc2control/releases/tag/0.1.0
