"""Events produced by the decoder layer."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class Overrun:
    """The firmware reported an overrun: samples were lost at this point.

    total is the firmware's running count of overruns, not the number of new
    ones. It is a uint16 on the board, so it wraps from 65535 to 0.
    """

    total: int


@dataclass(eq=False, frozen=True)
class SampleBlock:
    """Raw ADC values from 0 to 4095, without gaps inside the block.

    Consecutive blocks may have a gap between them, e.g. at an overrun.
    """

    samples: NDArray[np.uint16]


Event = SampleBlock | Overrun
