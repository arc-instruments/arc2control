ArC2Control User's Guide
========================

ArC TWO is our next generation electronic characterisation tool which enables
massive parallel testing of devices with arbitrary interconnections. It can
achieve sub-100 ns pulsing across 20 V of voltage.

You are reading this document because you recently acquired an ArC TWO. This
guide will cover installation, firmware management and basic usage. It is
mainly intended for end-users but there's separate :doc:`developer's guide
</api_modules>` if you want to start building upon the ArC TWO platform.


Minimum system requirements
---------------------------

ArC TWO requires a Windows 10/11 or Linux computer with at least 4 GB of RAM
(8 GB or more recommended). A USB-3.0 port is also required to allow ArC TWO to
operate at full speed. Please note that on Linux the minimum glibc supported by
ArC TWO is 2.14. This essentially means every distribution newer than CentOS 7.
Additionally libusb-1.0 is required which should be available on most
distributions released after 2015.  Linux systems based on musl libc (for
instance Alpine Linux) are not supported.


Getting started
---------------

Installation of the CESYS USB Drivers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ArC TWO is an FPGA-based tool and uses a Xilinix FPGA implementation provided
by CESYS GmbH: the EFM-03. In order for ArC TWO to operate you need to install
the CESYS USB Drivers for your operating system. On Windows you need to install
the udk3usb drivers from the `CESYS beastlink distribution`_
(beastlink-1.0-windows-free → driver → udk3usb-drivers-windows-1.3.exe). On Linux
scripts that generate packages for your distribution are available from `our
github <https://github.com/arc-instruments/beastlink-rs/tree/master/contrib>`_.

Out of the box
^^^^^^^^^^^^^^

The standard ArC TWO package comes with the following components: (a) The ArC
TWO board; (b) a 18 V power adaptor with its corresponding power module; (c) a
power module for external power supplies; (d) a PLCC32 daughterboard with
headers for probe-card support and (e) a USB-3.0 cable. Depending on your
configuration some components might be pre-assembled on ArC TWO.

.. figure:: images/out-of-the-box.jpg
   :alt: ArC TWO and standard accessories
   :align: center

   ArC TWO and standard accessories

To power up the board, plug in the provided AC power adaptor and flick the
power switch. If you intend to use a laboratory power supply instead remove the
retaining screws of the standard power module and replace it with the external
power supply module. Then tighten the retaining screws again and plug in an
external supply to the corresponding banana sockets. Please note that you need
**both 16.2 V and -16.2 V sources** and a minimum of 1 A on both to properly
power the board.

ArC TWO supports many different *daughterboards* for maximum connection
flexibility.  By default the 32NNA68 daughterboard is installed which exposes
all 64 channels of ArC TWO as header pins and also features a PLCC socket for
packaged samples.  Typical cavity sizes for these packages are (in inches)
0.265×0.265, 0.3×0.3, 0.4×0.4 and 0.46×0.46. Additional daughterboards are
available with SMA (32 channels) or BNC connectors (12 channels).

Installing the ArC TWO Control Panel
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ArC TWO Control Panel (ArC2Control) is a handy application that is oriented
towards crosspoint operations. That means that the ArC TWO channels are
organised in a 32 by 32 fashion essentially creating 32 different crosspoints.
In a crossbar configuration this allows for up to 1024 interconnection points.
This is by no means indicative of the full capabilities of ArC TWO but it's
a common enough scenario to have its own standalone application.

Since ArC2Control is still in active development the installation requires the
presence of a 64-bit Python interpreter. Please note that **32-bit interpreters
will not work**. Python versions > 3.8 are routinely tested and they should be
expected to work. On Windows we strongly recommend you install the `official
Python distribution <https://python.org>`_ instead of alternative distributions
such as Anaconda. On Linux you can use the Python interpreter that comes with
your distribution. Once Python is installed and available you can install
ArC2Control with the following command in a command line interpreter (any Linux
shell or Windows CMD or Powershell).

.. code-block:: console

   python -m pip install arc2control

Or, alternatively, for the latest development snapshot (requires `git
<https://git-scm.org>`_ to be available)

.. code-block:: console

   python -m pip install git+https://github.com/arc-instruments/arc2control

Please not that on Linux it is strongly recommended that you install
ArC2Control as a regular user, **not root**. Regardless of your installation
method you can launch ArC2Control with the following command

.. code-block:: console

   python -m arc2control

Using the ArC2Control Interface
-------------------------------

Overview
^^^^^^^^

ArC2Control is our recommended way to familiarise yourself with the ArC TWO
platform. It is divided into different functional panels.


.. figure:: images/gui-at-a-glance.svg
   :alt: Different panels of ArC2Control

   The different functional areas of ArC2Control

These are the following functional areas of ArC2Control:

* **Main Toolbar**: contains buttons that deal with dataset handling as well as
  firmware management.
* **Device History**: lists all experiments performed on devices defined by
  crosspoints.
* **Data Plot Panel**: displays all biasing history for the selected crosspoint
* **Connectivity Panel**: controls connection to ArC TWO, firmware selection and
  channel mapping management.
* **Manual operations**: handles manual biasing or reading actions performed to
  selected crosspoints.
* **Crossbar view**: Current resistance values of all devices in the crossbar.
* **Module panel**: Experiment panel management. Both built-in and external modules
  are available here.
* **Display and plotting options**: manages type of value to display (resistance,
  conductance, current), y-axis scale and number of historic data points to
  display.

Starting a new session
^^^^^^^^^^^^^^^^^^^^^^

When you first start ArC2Control you will be greeted with crossbar
configuration dialog which allows you to configure the size of the crossbar
that will be managed by ArC TWO.

.. figure:: images/crossbar-config.png
   :alt: Crossbar configuration dialog
   :align: center

   The crossbar configuration dialog

You can specify the size of the crossbar either manually, through a mapping
scheme or by loading an already existing dataset. In the latter case you can
additionally load the dataset in ArC2Control so that you can continue working
on it.

Connecting to ArC TWO and firmware management
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before connecting to ArC TWO you will need to install the firmware required by
the on-board FPGA. If no firmware is found, ArC2Control will prompt you to open
the firmware manager. You can also bring up the firmware manager by clicking
the corresponding button on the main toolbar.

.. figure:: images/firmware-manager.png
   :alt: The firmware management dialog
   :align: center

   The firmware management dialog - Firmware file **efm03_20211211_RF.bin** is
   already downloaded.

Clicking the *Refresh available firmwares* button (top right) will query the
ArC Instruments Server for available firmwares. It will then list all available
firmwares (newest first) on the right-hand panel. You can download the firmware
by clicking the *Download selected firmware* button which should then appear on
the locally installed firmwares on the left-hand panel. New firmwares will be
posted occasionally so check the firmware manager for updates. There are
several locations that ArC2Control can store firmware (see *Firmware download
path*). It is recommended that you use the user-local directory which is
``%APPDATA%/arc2control/firmwares`` on Windows or
``~/.local/share/arc2control/firmwares`` on Linux. Using a global directory
would allow you to share the firmware files among multiple users of the same
computer but in that case you need to start ArC2Control with elevated
permissions which is generally not recommended.

Closing the firmware manager will update the available firmwares available in
the *Connectivity Panel* on the main ArC2Control UI. If you have already
plugged in and powered-on an ArC TWO board the board ID will be available next
to *Connect/Disconnect ArC2* button. If not, connect and power-on an ArC TWO
board and press the *Refresh* button which should be populated with all
discovered device IDs. Make sure you select the firmware you downloaded (or any
other) so that it can be loaded on the instrument. Newest firmwares are listed
higher on the list. Upon successful connection the green *Connected* indicator
will lit up and you are now ready to use ArC TWO. Clicking the
*Connect/Disconnect ArC2* button will disconnect the tool and the red
*Disconnected* indicator will now appear.

.. _`CESYS beastlink distribution`: https://www.cesys.com/fileadmin/user_upload/service/FPGA/fpga%20boards%20%26%20modules/BeastLink/beastlink-1.0-windows-free.zip
