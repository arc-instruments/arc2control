import glob
import os

from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import get_module_file_attribute

binaries = []
hiddenimports = ["tomli._parser", "tomli._re", "tomli._types"]

if is_win:

    tomlidir = os.path.dirname(get_module_file_attribute('tomli'))
    sitepackages = os.path.dirname(tomlidir)
    dll_glob = os.path.join(sitepackages, '*__mypyc.*.pyd')
    if glob.glob(dll_glob):
        binaries.append((dll_glob, '.'))



