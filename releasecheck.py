#!/usr/bin/env python

import re
import os.path
import requests
import tomli
import sys
import json
import shutil
import semver
import subprocess


def latest_tag():
    git = shutil.which('git')

    cmd = [git, 'tag', '--sort=committerdate']

    lines = subprocess.check_output(cmd).decode().splitlines()

    try:
        return lines[-1]
    except IndexError:
        return None


def modver(module, basedir=None):

    if basedir is None:
        basedir = os.path.abspath(os.path.dirname(__file__))

    regexp = re.compile('^__version__\s*=\s*"(.*)"')
    with open(os.path.join(basedir, module, 'version.py'), 'r') as vfile:
        for line in vfile.readlines():
            match = regexp.match(line)
            if match is not None:
                return match.group(1).replace('-', '')
    return None


def internal_version():

    pyproject_tool = tomli.loads(open('pyproject.toml').read())['tool']['poetry']['version']

    versions = [pyproject_tool, modver('arc2control', os.path.dirname(__file__))]

    # Check if the same version is used throughout
    consistent = all(v == versions[0] for v in versions)
    if len(versions) < 2:
        raise ValueError('Not all of pyproject.toml or arc2control/version.py '
            'define versions')
    elif not consistent:
        # complain if it doesn't
        raise ValueError('pyproject.toml and arc2control/version.py '
            'have inconsistent versions')
    else:
        # return it otherwise
        return versions[0]


def pypi_versions():

    data = requests.get('https://pypi.org/pypi/arc2control/json')

    if data.status_code != 200:
        raise Exception('Could not determine PyPI version')

    content = json.loads(data.content)
    versions = list(content['releases'].keys())

    return versions


if __name__ == "__main__":

    if sys.argv[1] == 'commitcheck':
        try:
            iver = internal_version()
            print('Found internal version:', iver)
        except ValueError as err:
            print('Repository versions are not consistent', file=sys.stderr)
            sys.exit(1)

        maxver = latest_tag()

        if maxver is not None and semver.compare(maxver, iver) > 0:
            print('Current repository version is not higher than latest tag; '\
                'bump versions', file=sys.stderr)
            sys.exit(1)

    if sys.argv[1] == 'releasecheck':
        try:
            iver = internal_version()
            print('Found internal version:', iver)
        except ValueError as err:
            print('Repository versions are not consistent', file=sys.stderr)
            sys.exit(1)

        maxver = latest_tag()

        if maxver is not None and semver.compare(maxver, iver) > 0:
            print('Current repository version is not higher than latest tag; '\
                'bump versions', file=sys.stderr)
            sys.exit(1)

        try:
            pypivers = pypi_versions()
            print('Found all PyPI versions:', pypivers)
        except Exception as exc:
            print('A problem occurred when checking PyPI versions', exc, \
                file=sys.stderr)
            sys.exit(2)

        if iver in pypivers:
            print('An identical release exists on PyPI; bump versions '
                'before proceeding', file=sys.stderr)
            sys.exit(1)

    sys.exit(0)
