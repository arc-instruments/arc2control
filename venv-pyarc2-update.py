#!/usr/bin/python
import subprocess
import os.path
import sys


HERE = os.path.dirname(os.path.realpath(__file__))


def in_venv():
    return (hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


def main(path):

    print(sys.executable)

    subprocess.run([\
        sys.executable, '-m', 'pip',\
        'uninstall', '--yes', 'pyarc2'])

    subprocess.run([\
        sys.executable, '-m', 'pip',\
        'install', '--use-feature=in-tree-build', \
        path])

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

    sys.exit(main(pyarc2path))
