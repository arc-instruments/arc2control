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


def current_tag():
    try:
        out = subprocess.check_output([\
            'git', 'name-rev', '--name-only', '--no-undefined', '--tags', 'HEAD'],
            stderr=subprocess.DEVNULL)
        out = re.split('[\^\,\+]', out.decode().strip())
        semver.parse(out[0])
        return out[0]
    except (subprocess.CalledProcessError, ValueError):
        return None


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


def docs_version():

    regexp = re.compile('^release\s?=\s?(.*)$')
    lines = open(os.path.join(os.path.dirname(__file__), 'docs', 'conf.py')).readlines()

    for line in lines:
        line = line.strip()
        if regexp.match(line):
            m = regexp.match(line)
            return m.group(1).replace("'", "")

    raise ValueError('Could not determine docs version')


def internal_version():

    pyproject_tool = tomli.loads(open('pyproject.toml').read())['tool']['poetry']['version']
    versions = [pyproject_tool, docs_version(), modver('arc2control', os.path.dirname(__file__))]

    # Check if the same version is used throughout
    consistent = all(v == versions[0] for v in versions)
    if len(versions) < 3:
        raise ValueError('Not all of pyproject.toml, arc2control/version.py or docs/conf.py'
            'define versions')
    elif not consistent:
        # complain if it doesn't
        raise ValueError('pyproject.toml, arc2control/version.py and docs/conf.py '
            'have inconsistent versions: %s' % versions)
    else:
        # return it otherwise
        return versions[0]


def pypi_versions():

    data = requests.get('https://pypi.org/pypi/arc2control/json')

    # project not existing that's OK
    if data.status_code == 404:
        return []
    elif data.status_code != 200:
        raise Exception('Could not determine PyPI version: %d' % data.status_code)

    content = json.loads(data.content)
    versions = list(content['releases'].keys())

    return versions


if __name__ == "__main__":

    if sys.argv[1] == 'commitcheck':
        try:
            iver = internal_version()
            print('Found consistent internal version:', iver)
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
            print('Found consistent internal version:', iver)
        except ValueError as err:
            print('Repository versions are not consistent', file=sys.stderr)
            sys.exit(1)

        maxver = latest_tag()

        if maxver is None:
            print('Cannot find latest tag', file=sys.stderr)
            sys.exit(1)

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
