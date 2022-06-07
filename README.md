# ArC TWO™ Control Panel

This is the frontend application for ArC TWO. It exposes functionality mostly
related to crossbar configurations and provides a set of predefined
experiments suitable for general and (P/R/FE)RAM devices characterisation.

![](data/screenshots/arc2control-01-main.png)

## Instructions

ArC2Control leverages the [pyarc2](https://github.com/arc-instruments/pyarc2)
library to talk to ArC TWO. Since `pyarc2` is a native module and still under
development it is not automatically installed with ArC2Control and must be
installed separately.


### Building and running

As ArC2Control is still under development the recommended way to get started is
by using a virtual environment. ArC2Control uses
[poetry](https://python-poetry.org) to manage virtual environments.

* You will need a functional [Rust toolchain](https://rustup.rs). This
  requirement will be relaxed once prebuilt Python wheels for `pyarc2` are
  made available.
* You will also need a relatively new Python (≥ 3.8) and also have poetry
  installed (`python -m pip install poetry`). Pip must also be updated to at
  least version 20.x.
* Clone this repository.
* Initialise the virtual environment: `python -m poetry install`. This only needs
  to be done once.
* Install `pyarc2` into the virtual environment. This can easily be done with the
  included script
  `python -m poetry run python venv-pyarc2-update.py git+https://github.com/arc-instruments/pyarc2`.
  This will download `pyarc2` via git, build it and install it into the
  virtualenv. You can alternatively place the `pyarc2` repository along
  `arc2control` and run `venv-pyarc2-update.py` without additional arguments.
* Run the setup script `python -m poetry run python setup.py build`.
* Run ArC2Control `python -m poetry run python -m arc2control`.

## Custom modules

ArC2Control can be extended with custom experiment panels. An ArC2Control experiment
module is a standalone Python module that includes the following in its `__init__.py`.

```python
MOD_NAME = 'ModuleName'
MOD_DESCRIPTION = 'Description of said module'
MOD_TAG = 'MN' # a shorthand tag for the module
BUILT_IN = False

from .module import MainModule
# MainModule must derive from arc2control.modules.base.BaseModule`
ENTRY_POINT = MainModule
```

The built-in experiment modules are also built with the same infrastructure so
they can be used as a scaffold to build your own.
