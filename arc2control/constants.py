import importlib.util


def __pyarc2_exists():
    return importlib.util.find_spec('pyarc2') is not None


APP_NAME = 'arc2control'
APP_TITLE = 'ArC2 Control Panel'
EMODULES_DIR = 'arc2emodules'
FW_FILE_FILTER = 'Firmware files (*.bin);;Any file (*.*)'
H5_FILE_FILTER = 'Datasets (*.h5);;All files (*.*)'
H5_TS_EXPORT_FILTER = 'Comma separated file (*.csv);;Tab separated file (*.tsv)'
MOD_FILE_FILTER = 'JSON files (*.json);;All files (*.*)'
PYARC2_EXISTS = __pyarc2_exists()
ARC_FW_BASEURL = 'http://files.arc-instruments.co.uk/firmware/'

ARCFW_PUBKEY = """
-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEdwUFNsjRcBGWE4oOH/y/WDcFYzup
6U1ZxzvbIcgNq74nZds1DKlr8GgxBkchJsuWhwK7If6oTfRtr1LocfAKSA==
-----END PUBLIC KEY-----""".strip()
