ArC TWO specifications
======================

Reading operations
------------------

All precisions quoted are 3σ confidence intervals

Current measurement
^^^^^^^^^^^^^^^^^^^

* Accuracy: 1% at >16 nA, 10% at >1.6 nA
* Minimum current measurement: ±200 pA
* Maximum current measurement: ±10 mA
* Current measurement resolution: 2.6 pA
* Current measurement time: 1.5 ms

Voltage measurement
^^^^^^^^^^^^^^^^^^^

* Accuracy: 1% at >20 mV, 10% at >2 mV
* Minimum voltage measurement: ±200 μV
* Maximum voltage measurement: ±10 V
* Voltage measurement resolution: 77 μV
* Voltage measurment time: 10 μs (single sample), 320 μs (averaged)

Programming operations
----------------------

* Maximum bias voltage: ±13.5 V
* Bias voltage resolution: 305 μV at ±10 V, 610μ V at ±13.5 V
* Bias voltage current limit: 10 mA (200mA across all channels)
* Bias voltage slew rate: 400 mV/μs
* Arbitrary Pulse generator voltage: ±13.5 V
* Arbitrary Pulse generator width: 40 ns - inf
* Arbitrary Pulse generator time resolution: 10 ns
* Arbitrary Pulse generator current limit: 10 mA

Operation intervals
-------------------

* Minimum READ → WRITE interval: 20 μs
* Minimum WRITE → READ interval: 150 μs

Programmable I/O
----------------

* 64 fully independent SMU channels with pulse generators and access to
  unified current source
* 32 digital outputs with arbitrary high/low levels at ±13.5 V
* 32 digital I/Os with arbitrary high level at 1.8-5.5 V
* 4 arbitrary supplies at ±13.5 V and ±100 mA

Crossbar management
-------------------

* SMU configuration for up to 32×32 selector enabled crossbar array
* With 32NNA68 daughterboard (included as default):
   - Switchable header pin array for access to all channels
   - 68 pin PLCC socket for packaged samples (up to 1 kbit crossbar
     arrays)
* Optional 32-port SMA array and 12-port BNC array daughterboards for probe
  interface
* Optional 48-pin ZIF DIP socket daughterboard for use in general
  characterisation tasks with DIP packaged arrays.
