# toplevel module

import os
import logging
from .version import __version__ as VERSION

from PyQt6 import QtCore

ArC2ControlSettings = QtCore.QSettings('ArCInstruments', 'ArC2Control')


def __envToLogLevel():
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


def createLogger(name):

    level = __envToLogLevel()
    logger = logging.getLogger(name)
    logger.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('[%(levelname)s] [%(name)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger
