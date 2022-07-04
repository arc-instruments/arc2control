from setuptools import find_packages
from distutils.core import setup, Command
from distutils.command.build import build
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


class BuildUIs(Command):

    description = "Generate python files from Qt UI files"
    user_options = []

    def compile_ui(self, src, dst):
        """
        Compile UI file `src` into the python file `dst`. This is similar to
        what the pyuic script is doing but with some predefined values.
        """

        import PyQt6.uic as uic

        out = open(dst, 'w', encoding='utf-8')

        # see the docstring of PyQt6.uic.compileUi for more!
        uic.compileUi(src, out, execute=False, indent=4)
        out.close()

    def compile_base_uis(self):

        # Find the current working directory (ie. the folder this script resides
        # in). Then find out where the UI files are stored and setup the output
        # directory.
        uidir = os.path.join(__HERE__, 'uis')
        outdir = os.path.join(__HERE__, 'arc2control', 'widgets', 'generated')

        # Check if outdir exists but is not a directory; in that case
        # bail out!
        if not os.path.isdir(outdir) and os.path.exists(outdir):
            print("%s exists but is not a directory; aborting" % outdir)
            sys.exit(1)

        # Load up all UI files from `uidir`...
        uis = glob.glob(os.path.join(uidir, "*.ui"))
        generated = []

        # ... and convert them into python classes in `outdir`.
        for ui in uis:
            # target filename is the same as source with the .py suffix instead
            # of .ui.
            fname = os.path.splitext(os.path.basename(ui))[0]
            target = os.path.join(outdir, "%s.py" % fname)

            print("[UIC] Generating %s " % target, file=sys.stderr)
            self.compile_ui(ui, target)
            generated.append(target)

    def compile_module_uis(self):
        basedir = os.path.join(__HERE__, 'arc2control', 'modules')

        for moddir in glob.glob(os.path.join(basedir, '*')):
            # skip non dirs or __pycache__ directories
            if not os.path.isdir(moddir) or \
                os.path.basename(moddir) == '__pycache__':
                continue

            uidir = os.path.join(moddir, 'uis')

            if not os.path.isdir(uidir):
                print("[UIC] Module %s does not specify any uis, skipping" % \
                    os.path.basename(moddir), file=sys.stderr)
                continue

            outdir = os.path.join(moddir, 'generated')
            if not os.path.isdir(outdir):
                os.mkdir(outdir)

            initfile = os.path.join(outdir, '__init__.py')
            if os.path.exists(initfile) and (not os.path.isfile(initfile)):
                print("[UIC] Module %s initfile exists but it's not a file? Skipping" % \
                    initfile)
                continue
            if not os.path.exists(initfile):
                with open(initfile, mode='w') as f:
                    f.write('# arc2control.modules.%s' % os.path.basename(moddir))

            for ui in glob.glob(os.path.join(uidir, '*.ui')):
                fname = os.path.splitext(os.path.basename(ui))[0]
                target = os.path.join(outdir, "%s.py" % fname)
                print("[UIC] Generating %s" % target, file=sys.stderr)
                self.compile_ui(ui, target)


    def initialize_options(self):
        self.cwd = None

    def finalize_options(self):
        self.cwd = os.getcwd()

    def run(self):
        self.compile_base_uis()
        self.compile_module_uis()


class Build(build):

    user_options = build.user_options + []

    def run(self):
        self.run_command("build_uis")
        super().run()


cmdclass = {}
cmdclass['build_uis'] = BuildUIs
cmdclass['build'] = Build

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
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",

    ],
    packages = packages,
    python_requires = '>=3.8,<3.11',
    install_requires = requirements,
    entry_points = {
        'console_scripts': ['arc2control = arc2control.main:main']
    },
    package_data = {
        'arc2control': ['graphics/*png', 'graphics/*svg', 'version.txt',
            'mappings/*']
    },
    cmdclass = cmdclass
)
