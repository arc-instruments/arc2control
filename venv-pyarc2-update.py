#!/usr/bin/python
import subprocess
import os.path
import sys
import platform
import shutil
import re


ARCH = platform.architecture()[0]
HERE = os.path.dirname(os.path.realpath(__file__))
PIPRE = re.compile('^pyarc2\s+(.*)\s+pip$')


if sys.platform == 'win32':
    if ARCH == '32bit':
        DLLS = [
            'beastlink-1.0-x86.dll',
            'beastlink-1.0-x86.lib'
        ]
    elif ARCH == '64bit':
        DLLS = [
            'beastlink-1.0-x86_64.dll',
            'beastlink-1.0-x86_64.lib'
        ]
    else:
        raise OSError('Unsupported architecure: ' + ARCH)


def _find_pyarc2_install_path():
    out = subprocess.check_output([sys.executable, '-m', 'pip',\
        'list', '-v']).decode().splitlines()

    for entry in out:
        if entry.startswith('pyarc2'):
            (version, result) = PIPRE.match(entry).group(1).split(maxsplit=1)
            return os.path.join(result, 'pyarc2')

    return None


def in_venv():
    return (hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


def main(path):

    subprocess.run([\
        sys.executable, '-m', 'pip',\
        'uninstall', '--yes', 'pyarc2'])

    subprocess.run([\
        sys.executable, '-m', 'pip',\
        'install', '--use-feature=in-tree-build', \
        path])

    return 0


def main_win32(path):

    try:
        ipath = _find_pyarc2_install_path()
        for dll in DLLS:
            os.remove(os.path.join(ipath, dll))
    except Exception:
        # probably not installed
        pass

    ret = main(path)

    # failure
    if ret != 0:
        return ret

    try:
        ipath = _find_pyarc2_install_path()
    except Exception:
        print('Could not identify pyarc2 install path', file=sys.stderr)
        return 1

    if ipath is None:
        print('pyarc2 not installed in current venv', file=sys.stderr)
        return 1

    for dll in DLLS:
        shutil.copy(os.path.join(path, dll), ipath)

    return 0


if __name__ == "__main__":
    if not in_venv():
        print('This script is supposed to be run in a virtual environment',\
            file=sys.stderr)
        sys.exit(1)

    if '-h' in sys.argv[1:] or '--help' in sys.argv[1:]:
        print('%s [path]: Update pyarc2 in the current venv from path' % sys.argv[0],\
            file=sys.stderr)
        sys.exit(0)

    try:
        pyarc2path = sys.argv[1]
    except IndexError:
        there = os.path.join(HERE, '..', 'pyarc2')
        pyarc2path = os.path.realpath(there)

    if sys.platform in ['linux', 'linux2']:
        sys.exit(main(pyarc2path))
    elif sys.platform == 'win32':
        sys.exit(main_win32(pyarc2path))
    else:
        print('Unsupported platform:', sys.platform, file=sys.stderr)
        sys.exit(1)
