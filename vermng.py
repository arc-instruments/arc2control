#!/usr/bin/env python
import sys
import os.path
import re
import semver
from datetime import date


MODULE = 'arc2control'

VERFILETMPL = \
"""# THIS FILE IS UPDATED AUTOMATICALLY - DO NOT TOUCH
__version__ = "%s"
__copyright__ = "%s"
"""

def version_file(module, basedir=None):

    if basedir is None:
        basedir = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(basedir, module, 'version.py')


def pyproject_file(basedir=None):

    if basedir is None:
        basedir = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(basedir, 'pyproject.toml')


def find_version_from_file(module, basedir=None):

    regexp = re.compile('^__version__\s*=\s*"(.*)"')
    with open(os.path.join(version_file(module, basedir)), 'r') as vfile:
        for line in vfile.readlines():
            match = regexp.match(line)
            if match is not None:
                return match.group(1)
    return None


def update_version_file(module, version, basedir=None):
    versionfile = version_file(module, basedir)

    with open(versionfile, 'w') as verfile:
        thisyear = date.today().year
        if thisyear == 2022:
            copytext = "2022"
        else:
            copytext = "2022–%d" % thisyear
        verfile.write(VERFILETMPL % (version, copytext))


def update_pyproject(finalversion, basedir=None):

    orig = open(pyproject_file(basedir), 'r').read()

    lines = []

    in_section = False

    for line in orig.splitlines():
        line = line.strip()


        if re.match('\[tool.poetry\]', line):
            in_section = True

        if in_section and re.match('^version\s*=\s*".*"$', line):
            lines.append('version = "%s"' % finalversion)
        else:
            lines.append(line)

    with open(pyproject_file(basedir), 'w') as outfile:
        outfile.write("\n".join(lines))
        # add the final empty line if any
        if orig[-1] in ['\n', '\r\n']:
            outfile.write(orig[-1])


if __name__ == "__main__":

    try:
        action = sys.argv[1]
    except IndexError:
        print('No action specified', file=sys.stderr)
        sys.exit(1)

    cur_version = find_version_from_file(MODULE)
    ver_file = version_file(MODULE)

    if action == 'bump_major':
        finalversion = semver.bump_major(cur_version)
    elif action == 'bump_minor':
        finalversion = semver.bump_minor(cur_version)
    elif action == 'bump_patch':
        finalversion = semver.bump_patch(cur_version)
    elif action == 'bump_pre':
        parsed = semver.parse(cur_version)
        if parsed['prerelease'] is None:
            parsed = semver.parse(semver.bump_patch(cur_version))
            parsed['prerelease'] = 'rc0'
            finalversion = str(semver.VersionInfo(**parsed))
    elif action == 'clear_pre':
        parsed = semver.parse(cur_version)
        parsed['prerelease'] = None
        finalversion = str(semver.VersionInfo(**parsed))
    else:
        print('Unknown action:', action, file=sys.stderr)
        sys.exit(1)

    # remove dashes from prereleases
    finalversion = finalversion.replace('-', '')

    update_version_file(MODULE, finalversion)
    update_pyproject(finalversion)
