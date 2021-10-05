import subprocess
import os.path
import sys
import platform
import shutil
from distutils.spawn import find_executable
from distutils.dir_util import copy_tree, remove_tree

# This script is meant to help with Windows development where the
# beastlink libraries might not be in $PATH. This assumes that
# 1. libarc2, pyarc2 and arc2control are in the same directory
# 2. The beastlink libraries for this architecture are in the
#    top-level directory of pyarc2 (where Cargo.toml usually is)
# 3. Both beastlink-1.0-<ARCH>.dll and beastlink-1.0-<ARCH>.lib
#    are available
# 4. Poetry and maturin are installed in the current environment
# Do NOT use this script to prepare final packages for end-users
# instead build regular python wheels or use pyinstaller if on
# Windows.

HERE = os.path.realpath(os.path.dirname(__file__))
THERE = os.path.realpath(os.path.join(HERE, '..', 'pyarc2'))

ARCH = platform.architecture()[0]

DLLS_X32 = [
    'beastlink-1.0-x86.dll',
    'beastlink-1.0-x86.lib'
]
DLLS_X64 = [
    'beastlink-1.0-x86_64.dll',
    'beastlink-1.0-x86_64.lib'
]


def main():

    if platform.system() != 'Windows':
        print('This script is only meant for Windows development', file=sys.stderr)
        return 1

    os.chdir(THERE)
    subprocess.call([\
        sys.executable, '-m', 'poetry', 'run', 'maturin', 'develop'])
    os.chdir(HERE)

    LOCAL_PYARC2 = os.path.join(HERE, 'pyarc2')
    NEW_PYARC2 = os.path.join(THERE, 'pyarc2')

    if os.path.exists(LOCAL_PYARC2):
        if not os.path.isdir(LOCAL_PYARC2):
            print('%s is not a directory' % LOCAL_PYARC2, file=sys.stderr)
            return 1

        remove_tree(LOCAL_PYARC2)

    copy_tree(NEW_PYARC2, LOCAL_PYARC2)

    if ARCH == '32bit':
        dlls = DLLS_X32
    elif ARCH == '64bit':
        dlls = DLLS_X64
    else:
        print('Unknown architecture:', ARCH, file=sys.stderr)
        return 1

    for dll in dlls:
        print('Copying:', dll , file=sys.stderr)
        shutil.copy(os.path.join(THERE, dll), os.path.join(HERE, 'pyarc2'))

    print('Done!', file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
