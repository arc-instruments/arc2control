import os.path
try:
    import importlib.resources as importlib_resources
except (ModuleNotFoundError, ImportError):
    import importlib_resources

from PyQt6 import QtCore, QtGui, QtSvg


_pixmap_files = [
    'action-open.png',
    'action-save.png',
    'action-save-as.png',
    'action-new-dataset.png',
    'action-exit.png',
    'action-fw-manager.png',
    'action-delete.png',
    'action-download.png',
    'action-refresh.png',
    'action-cancel.png'
]

_svg_files = [
    'arc2-logo.svg',
    'splash.svg'
]

_all_images = {}


# WARNING: A QtWidgets.QApplication MUST be instantiated
# before loading the pixmaps from file!
def initialise():
    for x in _pixmap_files:
        with importlib_resources.path(__name__, x) as res:
            with open(res, 'rb') as f:

                img = os.path.splitext(x)[0]
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(f.read())

                _all_images[img] = pixmap

    for x in _svg_files:
        with importlib_resources.path(__name__, x) as res:
            with open(res, 'rb') as f:
                img = os.path.splitext(x)[0]
                svg = QtSvg.QSvgRenderer(f.read())
                pixmap = QtGui.QPixmap(svg.defaultSize().width(),\
                    svg.defaultSize().height())
                pixmap.fill(QtGui.QColorConstants.Transparent)
                painter = QtGui.QPainter(pixmap)
                svg.render(painter)
                _all_images[img] = pixmap


def getPixmap(name):
    return _all_images[name]


def getIcon(name):
    return QtGui.QIcon(_all_images[name])

