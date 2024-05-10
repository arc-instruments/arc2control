from pyarc2 import IdleMode
from dataclasses import dataclass


@dataclass
class ArC2Config:
    """
    Convenience dataclass to group ArC2 configuration options.
    """

    idleMode: IdleMode