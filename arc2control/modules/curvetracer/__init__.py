MOD_NAME = 'CurveTracer'
MOD_DESCRIPTION = 'I–V characterisation module'
MOD_TAG = 'CT'
BUILT_IN = True

from .curvetracer import CurveTracer
ENTRY_POINT = CurveTracer
