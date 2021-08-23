MOD_NAME = 'Retention'
MOD_TAG = 'RET'
MOD_DESCRIPTION = 'Read devices over time'
BUILT_IN = True

from .retention import Retention
ENTRY_POINT = Retention
