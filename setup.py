from setuptools import find_packages
from distutils.core import setup
import re, os, sys
import os.path
import glob
import time


def find_version_from_file(module, basedir=None):

    if basedir is None:
        basedir = os.path.abspath(os.path.dirname(__file__))

    regexp = re.compile('^__version__\s*=\s*"(.*)"')
    with open(os.path.join(basedir, module, 'version.py'), 'r') as vfile:
        for line in vfile.readlines():
            match = regexp.match(line)
            if match is not None:
                return match.group(1).replace('-', '')
    return None


__HERE__ = os.path.abspath(os.path.dirname(__file__))

__NAME__ = "arc2control"
__DESC__ = "ArC TWO Control Panel"
__MAINTAINER__ = "Spyros Stathopoulos"
__EMAIL__ = "devel@arc-instruments.co.uk"
__VERSION__ = find_version_from_file(__NAME__, __HERE__)
__URL__ = "http://www.arc-instruments.co.uk/products/arc-two/"

if os.path.exists(os.path.join(__HERE__, "README.md")):
    with open(os.path.join(__HERE__, "README.md"), encoding='utf-8') as readme:
        __LONG_DESC__ = readme.read()
else:
    __LONG_DESC__ = __DESC__


requirements = [
    'numpy>=1.18.0',
    'PyQt6>=6.1.0',
    'pyqtgraph>=0.12.3',
    'requests>=2.20.0',
    'semver>=2.0.0',
    'tomli>=1.0.0',
    'h5py>=3.0.0',
    'pyarc2>=0.1.0',
    'cryptography>=3.3.0'
]


# make sure we are not bundling local dev versions of pyqtgraph
packages = find_packages(exclude=['pyqtgraph', 'pyqtgraph.*'],
    include=['arc2control', 'arc2control.*'])

setup(
    name = __NAME__,
    version = __VERSION__,
    description = __DESC__,
    long_description = __LONG_DESC__,
    long_description_content_type = 'text/markdown',
    author = __MAINTAINER__,
    author_email = __EMAIL__,
    url = __URL__,
    project_urls = {
        "Bug Tracker": "https://github.com/arc-instruments/arc2control/issues",
        "Source Code": "https://github.com/arc-instruments/arc2control"
    },
    license = 'GPL3',
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: Microsoft :: Windows :: Windows 8",
        "Operating System :: Microsoft :: Windows :: Windows 8.1",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12"

    ],
    packages = packages,
    python_requires = '>=3.8,<3.12',
    install_requires = requirements,
    entry_points = {
        'console_scripts': ['arc2control = arc2control.main:main']
    },
    package_data = {
        'arc2control': ['graphics/*png', 'graphics/*svg', 'version.txt',
            'mappings/*', 'modules/*/uis/*.ui', 'widgets/uis/*.ui']
    },
)
