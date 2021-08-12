from enum import Enum

class Polarity(Enum):
    POSITIVE = 1
    NEGATIVE = 2

    def multiplier(self):
        if self == Polarity.POSITIVE:
            return 1.0
        elif self == Polarity.NEGATIVE:
            return -1.0
        else:
            raise Exception("Unknown polarity ?!")

