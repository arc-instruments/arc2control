from PyQt6 import QtCore, QtWidgets
from arc2control.widgets.app import App
import os.path
from . import graphics
from .mapper import ChannelMapper


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
            mods[mod.MOD_TAG] = (mod.MOD_NAME, mod.ENTRY_POINT)
            print("Importing module:", mod)
        except (ModuleNotFoundError, ImportError, KeyError, AttributeError) as exc:
            # either `MOD_NAME`/`ENTRY_POINT` are not defined, module
            # does not exist (for some reason) or module contains error
            print(exc)
            continue

    return mods


def main(args=None):

    import sys
    import warnings

    if args is None:
        args = sys.argv[1:]

    warnings.filterwarnings('ignore', category=RuntimeWarning, \
        message='.*invalid value encountered in true_divide.*', \
        module='arc2control\.widgets\..*')

    warnings.filterwarnings('ignore', category=RuntimeWarning, \
        message='.*divide by zero encountered in true_divide.*', \
        module='arc2control\.widgets\..*')

    realpath = os.path.dirname(os.path.realpath(__file__))
    mapfile = os.path.join(realpath, 'mappings', 'resarray32.toml')

    mapper = ChannelMapper.from_toml(mapfile)

    app = QtWidgets.QApplication(args)
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

