import glob
import os

from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import get_module_file_attribute

binaries = []

if is_win:

    pyarc2dir = os.path.dirname(get_module_file_attribute('pyarc2'))
    sitepackages = os.path.dirname(pyarc2dir)
    libdir = os.path.join(sitepackages, 'pyarc2.libs')
    dll_glob = os.path.join(libdir, '*.dll')
    if glob.glob(dll_glob):
        binaries.append((dll_glob, 'pyarc2.libs'))


