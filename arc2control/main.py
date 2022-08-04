from PyQt6 import QtCore, QtWidgets
from arc2control.widgets.app import App
from arc2control.widgets.crossbarconfig_dialog import CrossbarConfigDialog
import os.path
import glob
import logging
logger = logging.getLogger('LOAD')
from . import graphics
from . import constants
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
            logger.info("Importing module: %s" % mod)
        except (ModuleNotFoundError, ImportError, KeyError, AttributeError) as exc:
            # either `MOD_NAME`/`ENTRY_POINT` are not defined, module
            # does not exist (for some reason) or module contains error
            logger.warn('Module %s.%s could not be loaded: %s' % (base, name, exc))
            continue

    return mods


def _standardQtDirectories(name):
    return QtCore.QStandardPaths.locateAll(\
        QtCore.QStandardPaths.StandardLocation.AppDataLocation, \
        name, \
        QtCore.QStandardPaths.LocateOption.LocateDirectory)


def _envToLogLevel():
    level = os.environ.get('ARC2CTRL_LOGLEVEL', 'warn').strip().lower()

    if level == 'debug':
        return logging.DEBUG
    elif level == 'info':
        return logging.INFO
    elif level == 'warning' or level == 'warn':
        return logging.WARNING
    elif level == 'error':
        return logging.ERROR
    elif level == 'critical':
        return logging.CRITICAL
    else:
        return logging.WARNING


def main(args=None):

    logging.basicConfig(level=_envToLogLevel(), \
        format='[%(levelname)s] [%(name)s] %(message)s')

    import sys
    import warnings

    if args is None:
        args = sys.argv[1:]

    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32\
              .SetCurrentProcessExplicitAppUserModelID('ArC2 Control Panel')

    warnings.filterwarnings('ignore', category=RuntimeWarning, \
        message='.*invalid value encountered in true_divide.*', \
        module='arc2control\.widgets\..*')

    warnings.filterwarnings('ignore', category=RuntimeWarning, \
        message='.*divide by zero encountered in true_divide.*', \
        module='arc2control\.widgets\..*')

    app = QtWidgets.QApplication(args)
    app.setApplicationName(constants.APP_NAME)
    graphics.initialise()

    # Try to discover modules in QStandardPaths; locateAll will
    # produce a list of standard data locations with decreasing locality
    # (and therefore decreasing priority). Our data folder *MUST* contain
    # a python package named `arc2emodules` to qualify
    modulepaths = _standardQtDirectories(constants.EMODULES_DIR)

    # check all the module paths returned from `locateAll`
    for p in modulepaths:
        # check for an `__init__.py` file to find out if this
        # folder is indeed a python package
        if os.path.exists(os.path.join(p, '__init__.py')):
            # success, add it to the path. Since we are traversing
            # the paths from higher to lower priority, paths returned
            # first will have higher priority if modules of the same
            # name exist
            sys.path.append(os.path.dirname(p))
        else:
            logger.warn("%s exists but doesn't look like a package" % p)

    # discover built-in modules first
    from . import modules as basemodmod
    mods = _discover_modules(basemodmod.__path__)

    ## try to discover external modules now ##
    try:
        # this will only fail if there are no `arc2emodules` packages
        # found during the the loop above, there's nothing to do
        import arc2emodules as baseemodmod
        emods = _discover_modules(baseemodmod.__path__, constants.EMODULES_DIR)
    except ModuleNotFoundError:
        # no external modules
        emods = {}

    ## try to discover channel mappings ##
    mappers = {}

    # find all local mapping paths (~/.local/share, /usr/share, %APPDATA%,
    # %PYTHONDIR%, etc.)
    mappingpaths = _standardQtDirectories('mappings')
    # and add the built-in mappings as well (lowest priority)
    thispath = os.path.dirname(os.path.realpath(__file__))
    mappingpaths.append(os.path.join(thispath, 'mappings'))

    # reverse the mapping path list so that the most local directory
    # is last. it will overwrite all previous mappings with the same
    # name
    mappingpaths.reverse()

    for p in mappingpaths:
        for ff in glob.glob(os.path.join(thispath, p, '*.toml')):
            try:
                mapper = ChannelMapper.from_toml(ff)
                mappers[os.path.basename(ff)] = mapper
            except Exception as exc:
                logger.warn('Could not parse local mapping file %s; ignoring:' % \
                    os.path.basename(ff), exc)
                continue

    cnfdlg = CrossbarConfigDialog(mappers=mappers, parent=None)
    cnfdlg.show()
    if not cnfdlg.exec():
        return
    res = cnfdlg.result()

    # load the app, merging all modules into a dict
    wdg = App(mappers, shape=(res['nbits'], res['nwords']), \
        modules={**mods, **emods}, mapper=res['mapper'], \
        dset=res['dataset'])
    wdg.show()
    app.exec()

