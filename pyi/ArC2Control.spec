# PyInstaller spec file. This only targets Windows presently
# The script is driven from the following environment variables
#
# ARC2_PYI_PATHEX (optional): This is the full path of the arc2control source
# ARC2_PYI_CONSOLE (optional): Set to 0 to disable the console window

import os
import re
import sys
import os.path
import semver

from setuptools import find_packages
from pkgutil import iter_modules


def find_submodules(path, name=None):
    modules = set()

    for pkg in find_packages(path):
        if name:
            modules.add(name + '.' + pkg)
        else:
            modules.add(pkg)
        pkgpath = os.path.join(path, pkg.replace('.', '/'))

        for info in iter_modules([pkgpath]):
            if not info.ispkg:
                if name:
                    modules.add(name + '.' + pkg + '.' + info.name)
                else:
                    modules.add(pkg + '.' + info.name)
    return modules


def find_version():
    from arc2control import version
    return version.__version__

PATHEX = os.environ.get('ARC2_PYI_PATHEX', os.path.dirname(SPECPATH))
CONSOLE = bool(int(os.environ.get('ARC2_PYI_CONSOLE', 1)))


# DETERMINE VERSION

__VERSION_RAW__ = find_version()
__VERSION_SEMVER__ = semver.VersionInfo.parse(__VERSION_RAW__)

tmpl = open(os.path.join(PATHEX, 'pyi', 'win32-version-info.tmpl')).read()
version_keys = {'major': __VERSION_SEMVER__.major,
    'minor': __VERSION_SEMVER__.minor,
    'patch': __VERSION_SEMVER__.patch,
    'version_text': __VERSION_RAW__}
with open(os.path.join(PATHEX, 'build', 'arc2control', 'version_info.txt'), 'w') as version_file:
    version_file.write(tmpl.format(**version_keys))

# EXTRA FILES

added_files = [
    (os.path.join(PATHEX, 'arc2control/graphics/*.png'),'arc2control/graphics'),
    (os.path.join(PATHEX, 'arc2control/graphics/*.svg'),'arc2control/graphics'),
    (os.path.join(PATHEX, 'arc2control/mappings/*.toml'),'arc2control/mappings'),
]

# MODULES

modimports = [
    'pyqtgraph',
    'pyarc2',
    'arc2control',
    'arc2control.modules']

# BUILT-IN MODULES

for m in ['curvetracer', 'retention']:
    print('Adding built-in module', m)
    modimports.append('arc2control.modules.%s' % m)
    if os.path.exists(os.path.join('arc2control', 'modules', m, 'generated')):
        modimports.append('arc2control.modules.%s.generated' % m)

# PYQTGRAPH DYNAMIC IMPORTS

# pyqtgraph has dynamic import of modules based on PyQt version. PyInstaller
# will not pick these up so we need to find them and add them manually. We are
# including the Qt6 modules only
import pyqtgraph
allpyqtgraphmods = find_submodules(os.path.dirname(pyqtgraph.__file__), name='pyqtgraph')
for mod in allpyqtgraphmods:
    if mod.endswith('Template_pyqt6') and not 'example' in mod:
        print('Adding pyqtgraph hidden import:', mod)
        modimports.append(mod)


a = Analysis([os.path.join(PATHEX, 'pyi', 'pyi-stub.py')],
    pathex=[PATHEX],
    binaries=None,
    datas=added_files,
    hiddenimports=modimports,
    hookspath=[os.path.join(PATHEX, 'pyi')],
    runtime_hooks=[],
    excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter',
        'Tkinter', 'IPython', 'jedi', 'matplotlib', 'PyQt4',
        'PyQt5'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(pyz,
    a.scripts,
    exclude_binaries=True,
    name='arc2control',
    debug=False,
    strip=False,
    upx=True,
    icon=os.path.join(PATHEX, 'pyi', 'appicon.ico'),
    console=CONSOLE,
    version=os.path.join(PATHEX, 'build', 'arc2control', 'version_info.txt'))

coll = COLLECT(exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='arc2control')

# vim:ft=python
